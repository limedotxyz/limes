import asyncio
import json
import socket
import time
import uuid
from queue import Queue
from typing import Optional

from lime.config import (
    BOOTSTRAP_PEERS,
    HEARTBEAT_INTERVAL,
    MULTICAST_GROUP,
    MULTICAST_PORT,
    PEER_TIMEOUT,
    POW_DIFFICULTY,
    PRUNE_INTERVAL,
    RELAY_SERVERS,
    TCP_PORT_DEFAULT,
)
from lime.crypto import verify
from lime.encryption import (
    generate_room_key,
    signing_to_curve_private,
    verify_to_curve_public,
    curve_public_from_hex,
    seal_room_key,
    unseal_room_key,
    encrypt_message,
    decrypt_message,
)
from lime.message import Message, verify_pow
from lime.store import MessageStore

try:
    import websockets
except ImportError:
    websockets = None


class Peer:
    __slots__ = ("name", "tag", "pubkey", "reader", "writer", "address", "last_seen")

    def __init__(self, name, tag, pubkey, reader, writer, address):
        self.name = name
        self.tag = tag
        self.pubkey = pubkey
        self.reader: asyncio.StreamReader = reader
        self.writer: asyncio.StreamWriter = writer
        self.address = address
        self.last_seen = time.time()

    @property
    def display(self):
        return f"{self.name}#{self.tag}"

    def is_alive(self):
        return time.time() - self.last_seen < PEER_TIMEOUT


class Network:
    def __init__(
        self,
        name: str,
        tag: str,
        pubkey_hex: str,
        signing_key,
        store: MessageStore,
        ui_queue: Queue,
        tcp_port: int = TCP_PORT_DEFAULT,
    ):
        self.name = name
        self.tag = tag
        self.pubkey_hex = pubkey_hex
        self.signing_key = signing_key
        self.store = store
        self.ui_queue = ui_queue
        self.tcp_port = tcp_port

        self.peers: dict[str, Peer] = {}
        self.claimed_names: dict[str, str] = {}
        self.seen_ids: set[str] = set()
        self._running = False
        self._server: Optional[asyncio.Server] = None

        # Relay privacy layer
        self._relay_ws: dict[str, object] = {}
        self.relay_wallet: str | None = None
        self._session_id = str(uuid.uuid4())
        self._curve_private = signing_to_curve_private(signing_key)
        self._curve_public = verify_to_curve_public(signing_key.verify_key)
        self._curve_pk_hex = self._curve_public.encode().hex()
        self._room_key: bytes | None = None
        self._room_key_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        self._running = True
        self.claimed_names[self.name] = self.pubkey_hex

        port = self.tcp_port
        for attempt in range(10):
            try:
                self._server = await asyncio.start_server(
                    self._on_incoming, "0.0.0.0", port,
                )
                self.tcp_port = port
                break
            except OSError:
                port += 1
        else:
            self.ui_queue.put(("error", "Could not bind TCP port"))
            return

        await self._server.start_serving()
        asyncio.create_task(self._multicast_listener())
        asyncio.create_task(self._multicast_announce())
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._prune_loop())

        for relay_url in RELAY_SERVERS:
            asyncio.create_task(self._relay_connect(relay_url))

        self.ui_queue.put(("status", f"listening on port {self.tcp_port}"))

    async def stop(self):
        self._running = False
        if self._server:
            self._server.close()
        for peer in list(self.peers.values()):
            try:
                peer.writer.close()
            except Exception:
                pass
        for ws in self._relay_ws.values():
            try:
                await ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # WebSocket relay — anonymous encrypted channel
    # ------------------------------------------------------------------

    async def _relay_connect(self, url: str):
        if websockets is None:
            self.ui_queue.put(("error", "websockets not installed \u2014 relay disabled"))
            return

        while self._running:
            try:
                async with websockets.connect(url) as ws:
                    self._relay_ws[url] = ws
                    self.ui_queue.put(("status", "relay connected"))

                    # Anonymous hello — no name, no tag, no signing key
                    hello = json.dumps({
                        "type": "hello",
                        "session": self._session_id,
                        "curve_pk": self._curve_pk_hex,
                    })
                    await ws.send(hello)

                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        await self._relay_dispatch(data, ws)

            except Exception:
                self._relay_ws.pop(url, None)

            if self._running:
                await asyncio.sleep(5)

    async def _relay_dispatch(self, data: dict, ws):
        t = data.get("type")

        if t == "relay_peers":
            peers = data.get("peers", [])
            count = data.get("count", len(peers))
            if count > 0:
                self.ui_queue.put(("status", f"relay: {count} peers online"))
            if peers and self._room_key is None:
                await ws.send(json.dumps({
                    "type": "key_request",
                    "session": self._session_id,
                    "curve_pk": self._curve_pk_hex,
                }))
                asyncio.create_task(self._key_timeout())
            elif not peers:
                self._room_key = generate_room_key()
                self._room_key_event.set()
                self.ui_queue.put(("e2e", True))

        elif t == "relay_join":
            self.ui_queue.put(("peer_joined", "a peer"))
            peer_curve_pk = data.get("curve_pk", "")
            peer_session = data.get("session", "")
            if self._room_key and peer_curve_pk:
                try:
                    recipient_pk = curve_public_from_hex(peer_curve_pk)
                    sealed = seal_room_key(self._room_key, recipient_pk)
                    await ws.send(json.dumps({
                        "type": "key_share",
                        "to": peer_session,
                        "sealed": sealed,
                    }))
                except Exception:
                    pass

        elif t == "relay_leave":
            self.ui_queue.put(("peer_left", "a peer"))

        elif t == "key_share":
            if self._room_key is None:
                try:
                    sealed = data.get("sealed", "")
                    self._room_key = unseal_room_key(sealed, self._curve_private)
                    self._room_key_event.set()
                    self.ui_queue.put(("e2e", True))
                except Exception:
                    pass

        elif t == "key_request":
            peer_session = data.get("session", "")
            peer_curve_pk = data.get("curve_pk", "")
            if self._room_key and peer_curve_pk and peer_session != self._session_id:
                try:
                    recipient_pk = curve_public_from_hex(peer_curve_pk)
                    sealed = seal_room_key(self._room_key, recipient_pk)
                    await ws.send(json.dumps({
                        "type": "key_share",
                        "to": peer_session,
                        "sealed": sealed,
                    }))
                except Exception:
                    pass

        elif t == "msg":
            if self._room_key:
                try:
                    envelope = data.get("envelope", "")
                    plaintext = decrypt_message(envelope, self._room_key)
                    msg_data = json.loads(plaintext)
                    await self._handle_msg(msg_data, from_peer=None)
                except Exception:
                    pass

        elif t == "relay_wallet":
            self.relay_wallet = data.get("address")

    async def _key_timeout(self):
        """Generate own room key if no one shares one within 10 seconds."""
        try:
            await asyncio.wait_for(self._room_key_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            if self._room_key is None:
                self._room_key = generate_room_key()
                self._room_key_event.set()
                self.ui_queue.put(("e2e", True))

    async def _relay_broadcast(self, msg: Message):
        """Encrypt and send a message through all connected relays."""
        if self._room_key is None:
            return
        plaintext = json.dumps(msg.to_dict()).encode()
        envelope = encrypt_message(plaintext, self._room_key)
        payload = json.dumps({"type": "msg", "envelope": envelope})
        for url, ws in list(self._relay_ws.items()):
            try:
                await ws.send(payload)
            except Exception:
                self._relay_ws.pop(url, None)

    # ------------------------------------------------------------------
    # TCP — outbound
    # ------------------------------------------------------------------

    async def connect_to(self, host: str, port: int):
        for p in self.peers.values():
            if p.pubkey == self.pubkey_hex:
                return
            if p.address and p.address[0] == host and p.address[1] == port:
                return
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except Exception:
            self.ui_queue.put(("error", "peer connection failed"))
            return
        await self._handshake(reader, writer, (host, port), outbound=True)

    # ------------------------------------------------------------------
    # TCP — inbound
    # ------------------------------------------------------------------

    async def _on_incoming(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        await self._handshake(reader, writer, addr, outbound=False)

    # ------------------------------------------------------------------
    # Handshake (symmetric after the first write)
    # ------------------------------------------------------------------

    async def _handshake(self, reader, writer, addr, outbound: bool):
        hello = json.dumps({
            "type": "hello",
            "name": self.name,
            "tag": self.tag,
            "pubkey": self.pubkey_hex,
            "tcp_port": self.tcp_port,
        }) + "\n"
        try:
            writer.write(hello.encode())
            await writer.drain()

            raw = await asyncio.wait_for(reader.readline(), timeout=10)
            data = json.loads(raw.decode().strip())
        except Exception:
            writer.close()
            return

        if data.get("type") != "hello":
            writer.close()
            return

        peer_name = data["name"]
        peer_tag = data["tag"]
        peer_pubkey = data["pubkey"]
        peer_id = f"{peer_name}#{peer_tag}"

        if peer_pubkey == self.pubkey_hex:
            writer.close()
            return

        if peer_id in self.peers:
            writer.close()
            return

        if peer_name in self.claimed_names and self.claimed_names[peer_name] != peer_pubkey:
            reject = json.dumps({"type": "name_taken", "name": peer_name}) + "\n"
            writer.write(reject.encode())
            await writer.drain()
            writer.close()
            return

        self.claimed_names[peer_name] = peer_pubkey
        peer = Peer(peer_name, peer_tag, peer_pubkey, reader, writer, addr)
        self.peers[peer_id] = peer
        self.ui_queue.put(("peer_joined", peer_id))

        await self._sync_store(peer)
        asyncio.create_task(self._listen(peer))

    # ------------------------------------------------------------------
    # Sync — send all current messages to a newly connected peer
    # ------------------------------------------------------------------

    async def _sync_store(self, peer: Peer):
        for msg in self.store.get_all():
            line = json.dumps({"type": "msg", "data": msg.to_dict()}) + "\n"
            try:
                peer.writer.write(line.encode())
            except Exception:
                return
        try:
            await peer.writer.drain()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Listener — read NDJSON lines from a peer
    # ------------------------------------------------------------------

    async def _listen(self, peer: Peer):
        try:
            while self._running:
                raw = await peer.reader.readline()
                if not raw:
                    break
                if len(raw) > 65536:
                    continue
                try:
                    data = json.loads(raw.decode().strip())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                await self._dispatch(data, peer)
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            await self._drop_peer(peer)

    async def _dispatch(self, data: dict, from_peer: Peer):
        from_peer.last_seen = time.time()
        t = data.get("type")
        if t == "msg":
            await self._handle_msg(data.get("data", {}), from_peer)
        elif t == "heartbeat":
            pass
        elif t == "name_taken":
            self.ui_queue.put(("error", f"Name '{data.get('name')}' is taken on the network"))

    # ------------------------------------------------------------------
    # Incoming message handling
    # ------------------------------------------------------------------

    async def _handle_msg(self, raw: dict, from_peer: Optional[Peer]):
        try:
            msg = Message.from_dict(raw)
        except Exception:
            return

        if msg.id in self.seen_ids:
            return
        self.seen_ids.add(msg.id)

        if msg.is_expired:
            return

        if not verify_pow(msg.pow_payload(), msg.nonce, msg.pow_hash, POW_DIFFICULTY):
            return

        if not verify(msg.author_pubkey, msg.signature, msg.signable_payload()):
            return

        if msg.author_name in self.claimed_names:
            if self.claimed_names[msg.author_name] != msg.author_pubkey:
                return

        if self.store.add(msg):
            self.ui_queue.put(("new_msg", msg))
            await self._gossip(msg, exclude=from_peer)

    # ------------------------------------------------------------------
    # Broadcast / gossip
    # ------------------------------------------------------------------

    async def broadcast(self, msg: Message):
        self.seen_ids.add(msg.id)
        line = json.dumps({"type": "msg", "data": msg.to_dict()}) + "\n"
        encoded = line.encode()
        for peer in list(self.peers.values()):
            try:
                peer.writer.write(encoded)
                await peer.writer.drain()
            except Exception:
                await self._drop_peer(peer)

        await self._relay_broadcast(msg)

    async def _gossip(self, msg: Message, exclude: Optional[Peer]):
        line = json.dumps({"type": "msg", "data": msg.to_dict()}) + "\n"
        encoded = line.encode()
        for peer in list(self.peers.values()):
            if peer is exclude:
                continue
            try:
                peer.writer.write(encoded)
                await peer.writer.drain()
            except Exception:
                await self._drop_peer(peer)

        await self._relay_broadcast(msg)

    # ------------------------------------------------------------------
    # Peer management
    # ------------------------------------------------------------------

    async def _drop_peer(self, peer: Peer):
        peer_id = f"{peer.name}#{peer.tag}"
        if peer_id in self.peers:
            del self.peers[peer_id]
            if peer.name in self.claimed_names:
                if self.claimed_names[peer.name] == peer.pubkey:
                    del self.claimed_names[peer.name]
            self.ui_queue.put(("peer_left", peer_id))
        try:
            peer.writer.close()
        except Exception:
            pass

    def peer_count(self) -> int:
        return len(self.peers)

    def peer_names(self) -> list[str]:
        return [p.name for p in self.peers.values()]

    # ------------------------------------------------------------------
    # UDP multicast — LAN discovery
    # ------------------------------------------------------------------

    async def _multicast_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", MULTICAST_PORT))
            group = socket.inet_aton(MULTICAST_GROUP)
            mreq = group + socket.inet_aton("0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except Exception:
            return
        sock.setblocking(False)
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                data, addr = await loop.sock_recvfrom(sock, 2048)
                info = json.loads(data.decode())
                if info.get("type") != "discover":
                    continue
                if info.get("pubkey") == self.pubkey_hex:
                    continue
                peer_id = f"{info['name']}#{info['tag']}"
                if peer_id not in self.peers:
                    host = addr[0]
                    port = info.get("tcp_port", TCP_PORT_DEFAULT)
                    asyncio.create_task(self.connect_to(host, port))
            except Exception:
                await asyncio.sleep(1)

    async def _multicast_announce(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        payload = json.dumps({
            "type": "discover",
            "name": self.name,
            "tag": self.tag,
            "pubkey": self.pubkey_hex,
            "tcp_port": self.tcp_port,
        }).encode()
        while self._running:
            try:
                sock.sendto(payload, (MULTICAST_GROUP, MULTICAST_PORT))
            except Exception:
                pass
            await asyncio.sleep(10)

    # ------------------------------------------------------------------
    # Background maintenance
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self):
        while self._running:
            hb = json.dumps({"type": "heartbeat", "name": self.name, "tag": self.tag}) + "\n"
            encoded = hb.encode()
            for peer in list(self.peers.values()):
                if not peer.is_alive():
                    await self._drop_peer(peer)
                    continue
                try:
                    peer.writer.write(encoded)
                    await peer.writer.drain()
                except Exception:
                    await self._drop_peer(peer)
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _prune_loop(self):
        while self._running:
            self.store.prune()
            if len(self.seen_ids) > 10_000:
                self.seen_ids.clear()
            await asyncio.sleep(PRUNE_INTERVAL)
