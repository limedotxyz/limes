"""
Lime scanner — a full peer that decrypts messages and serves them to limescan.

Unlike the relay (which is a blind pipe), the scanner is a participant
in the network. It receives the room key, decrypts messages, and
streams them to the limescan web frontend over a local WebSocket.

Architecture:
  relay (dumb pipe, encrypted) <--ws--> scanner (full peer, decrypts)
                                            |
                                            v
                                        browser (limescan.xyz)

Run with: lime scanner [--relay ws://relay:4210] [--port 3001]
"""

import asyncio
import json
import time
import uuid

try:
    import websockets
    from websockets.asyncio.server import serve
except ImportError:
    websockets = None
    serve = None

from lime.config import MESSAGE_TTL, POW_DIFFICULTY, RELAY_SERVERS
from lime.crypto import generate_keypair, verify
from lime.encryption import (
    curve_public_from_hex,
    decrypt_message,
    generate_room_key,
    seal_room_key,
    signing_to_curve_private,
    unseal_room_key,
    verify_to_curve_public,
)
from lime.message import Message, verify_pow

DEFAULT_SCANNER_PORT = 4211

_browser_clients: set = set()
_recent_messages: list = []
_active_authors: dict[str, float] = {}  # name#tag -> last seen timestamp
_stats = {
    "peers_online": 0,
    "total_messages": 0,
    "start_time": 0,
}
_relay_wallet: str | None = None


async def _broadcast_to_browsers(event: dict):
    if not _browser_clients:
        return
    encoded = json.dumps(event)
    dead = []
    for ws in _browser_clients:
        try:
            await ws.send(encoded)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _browser_clients.discard(ws)


async def _handle_browser(ws):
    _browser_clients.add(ws)
    try:
        now = time.time()
        active = [m for m in _recent_messages if now - m["timestamp"] < m.get("ttl", MESSAGE_TTL)]
        authors = [
            name for name, ts in _active_authors.items()
            if now - ts < MESSAGE_TTL
        ]
        await ws.send(json.dumps({
            "type": "snapshot",
            "peers_online": _stats["peers_online"],
            "peers": authors,
            "total_messages": _stats["total_messages"],
            "uptime": now - _stats["start_time"],
            "relay_wallet": _relay_wallet,
            "recent_messages": [{"data": m, "relayed_at": m.get("timestamp", now)} for m in active],
        }))
        async for _ in ws:
            pass
    except Exception:
        pass
    finally:
        _browser_clients.discard(ws)


async def run_scanner(
    relay_url: str,
    scanner_port: int = DEFAULT_SCANNER_PORT,
    scanner_host: str = "0.0.0.0",
):
    global _relay_wallet
    if websockets is None:
        print("ERROR: websockets package required.")
        return

    _stats["start_time"] = time.time()

    sk, vk = generate_keypair()
    curve_private = signing_to_curve_private(sk)
    curve_public = verify_to_curve_public(vk)
    curve_pk_hex = curve_public.encode().hex()
    session_id = str(uuid.uuid4())

    room_key: list[bytes | None] = [None]  # mutable container
    room_key_event = asyncio.Event()
    seen_ids: set[str] = set()

    async def relay_loop():
        global _relay_wallet

        while True:
            try:
                async with websockets.connect(relay_url) as ws:
                    await ws.send(json.dumps({
                        "type": "hello",
                        "session": session_id,
                        "curve_pk": curve_pk_hex,
                    }))

                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        t = data.get("type")

                        if t == "relay_peers":
                            peers = data.get("peers", [])
                            _stats["peers_online"] = data.get("count", len(peers))
                            if peers and room_key[0] is None:
                                await ws.send(json.dumps({
                                    "type": "key_request",
                                    "session": session_id,
                                    "curve_pk": curve_pk_hex,
                                }))
                            elif not peers:
                                room_key[0] = generate_room_key()
                                room_key_event.set()

                        elif t == "relay_join":
                            _stats["peers_online"] += 1
                            peer_curve_pk = data.get("curve_pk", "")
                            peer_session = data.get("session", "")
                            await _broadcast_to_browsers({
                                "type": "peer_join",
                                "peers_online": _stats["peers_online"],
                                "ts": data.get("ts", time.time()),
                            })
                            if room_key[0] and peer_curve_pk:
                                try:
                                    rpk = curve_public_from_hex(peer_curve_pk)
                                    sealed = seal_room_key(room_key[0], rpk)
                                    await ws.send(json.dumps({
                                        "type": "key_share",
                                        "to": peer_session,
                                        "sealed": sealed,
                                    }))
                                except Exception:
                                    pass

                        elif t == "relay_leave":
                            _stats["peers_online"] = max(0, _stats["peers_online"] - 1)
                            await _broadcast_to_browsers({
                                "type": "peer_leave",
                                "peers_online": _stats["peers_online"],
                                "ts": time.time(),
                            })

                        elif t == "key_share":
                            if room_key[0] is None:
                                try:
                                    sealed = data.get("sealed", "")
                                    room_key[0] = unseal_room_key(sealed, curve_private)
                                    room_key_event.set()
                                except Exception:
                                    pass

                        elif t == "key_request":
                            peer_session = data.get("session", "")
                            peer_curve_pk = data.get("curve_pk", "")
                            if room_key[0] and peer_curve_pk and peer_session != session_id:
                                try:
                                    rpk = curve_public_from_hex(peer_curve_pk)
                                    sealed = seal_room_key(room_key[0], rpk)
                                    await ws.send(json.dumps({
                                        "type": "key_share",
                                        "to": peer_session,
                                        "sealed": sealed,
                                    }))
                                except Exception:
                                    pass

                        elif t == "msg":
                            _stats["total_messages"] += 1
                            if room_key[0]:
                                try:
                                    envelope = data.get("envelope", "")
                                    plaintext = decrypt_message(envelope, room_key[0])
                                    msg_data = json.loads(plaintext)
                                    msg = Message.from_dict(msg_data)

                                    if msg.id in seen_ids:
                                        continue
                                    seen_ids.add(msg.id)
                                    if msg.is_expired:
                                        continue
                                    if not verify_pow(msg.pow_payload(), msg.nonce, msg.pow_hash, POW_DIFFICULTY):
                                        continue
                                    if not verify(msg.author_pubkey, msg.signature, msg.signable_payload()):
                                        continue

                                    md = msg.to_dict()
                                    _recent_messages.append(md)

                                    author = f"{msg.author_name}#{msg.author_tag}"
                                    _active_authors[author] = time.time()

                                    now = time.time()
                                    _recent_messages[:] = [
                                        m for m in _recent_messages
                                        if now - m["timestamp"] < m.get("ttl", MESSAGE_TTL)
                                    ]
                                    expired_authors = [
                                        a for a, ts in _active_authors.items()
                                        if now - ts > MESSAGE_TTL
                                    ]
                                    for a in expired_authors:
                                        del _active_authors[a]

                                    await _broadcast_to_browsers({
                                        "type": "message",
                                        "data": md,
                                        "relayed_at": time.time(),
                                    })
                                except Exception:
                                    pass

                        elif t == "relay_wallet":
                            _relay_wallet = data.get("address")

            except Exception:
                pass

            await asyncio.sleep(5)

    print()
    print("  limes scanner")
    print("  " + "-" * 14)
    print(f"  relay: {relay_url}")
    print(f"  web server: ws://{scanner_host}:{scanner_port}")
    print()
    print("  the scanner is a full peer -- it can decrypt messages.")
    print("  relay operators cannot see message content.")
    print()

    asyncio.create_task(relay_loop())

    async with serve(_handle_browser, scanner_host, scanner_port):
        while True:
            await asyncio.sleep(30)
            now = time.time()
            active = len([m for m in _recent_messages if now - m["timestamp"] < m.get("ttl", MESSAGE_TTL)])
            print(f"  [scanner: {len(_browser_clients)} browsers | {active} active msgs | {_stats['total_messages']} total]")


def main(relay_url: str | None = None, port: int | None = None):
    import os
    if port is None:
        port = int(os.environ.get("PORT", DEFAULT_SCANNER_PORT))
    if not relay_url:
        relay_url = RELAY_SERVERS[0] if RELAY_SERVERS else "ws://localhost:4210"
    asyncio.run(run_scanner(relay_url=relay_url, scanner_port=port))


if __name__ == "__main__":
    main()
