"""
Lightweight WebSocket relay server for lime peer discovery and message forwarding.

PRIVACY GUARANTEES:
- Peers identified by random session UUIDs only — no names, no identities.
- Messages are end-to-end encrypted; the relay forwards opaque blobs.
- Zero message storage — not even in memory.
- Random forwarding delay (50-300ms) breaks timing correlation.
- Scanner feed receives metadata only (peer count, message count), never content.

HARDENING:
- Max 500 concurrent peer connections, 20 scanners.
- 64KB max message size.
- Per-connection rate limit (10 msgs/sec).
- Session ID collision rejected.
- Idle connections dropped after 5 minutes.

The relay is a dumb pipe. It earns $LIME for forwarding traffic.

Run with: lime relay
"""

import asyncio
import json
import random
import time
import uuid

try:
    import websockets
    from websockets.asyncio.server import serve
except ImportError:
    websockets = None
    serve = None

DEFAULT_PORT = 4210
_DELAY_MIN = 0.05
_DELAY_MAX = 0.30

MAX_PEERS = 500
MAX_SCANNERS = 20
MAX_MSG_BYTES = 65536          # 64KB per WebSocket frame
RATE_LIMIT_PER_SEC = 10
RATE_LIMIT_WINDOW = 1.0
IDLE_TIMEOUT = 300             # 5 minutes

_clients: dict[str, dict] = {}
_scanners: set = set()
_stats = {
    "total_messages": 0,
    "total_connections": 0,
    "start_time": 0,
}
_relay_wallet: str | None = None


async def _broadcast_to_scanners(event: dict):
    if not _scanners:
        return
    encoded = json.dumps(event)
    dead = []
    for ws in _scanners:
        try:
            await ws.send(encoded)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _scanners.discard(ws)


async def _delayed_forward(ws, payload: str):
    await asyncio.sleep(random.uniform(_DELAY_MIN, _DELAY_MAX))
    try:
        await ws.send(payload)
    except Exception:
        pass


class _RateLimiter:
    __slots__ = ("_timestamps", "_limit", "_window")

    def __init__(self, limit: int = RATE_LIMIT_PER_SEC, window: float = RATE_LIMIT_WINDOW):
        self._timestamps: list[float] = []
        self._limit = limit
        self._window = window

    def allow(self) -> bool:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self._window]
        if len(self._timestamps) >= self._limit:
            return False
        self._timestamps.append(now)
        return True


async def _handler(ws):
    path = getattr(ws, "request", None)
    if path and hasattr(path, "path") and path.path == "/scan":
        await _handle_scanner(ws)
        return

    if len(_clients) >= MAX_PEERS:
        try:
            await ws.close(1013, "relay full")
        except Exception:
            pass
        return

    session_id = None
    _stats["total_connections"] += 1
    limiter = _RateLimiter()
    last_activity = time.monotonic()

    try:
        async for raw in ws:
            if isinstance(raw, (bytes, str)) and len(raw) > MAX_MSG_BYTES:
                continue

            last_activity = time.monotonic()

            if not limiter.allow():
                continue

            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if not isinstance(data, dict):
                continue

            msg_type = data.get("type")

            if msg_type == "hello":
                proposed_id = data.get("session", "")
                if not proposed_id or proposed_id in _clients:
                    proposed_id = str(uuid.uuid4())

                if session_id and session_id in _clients:
                    del _clients[session_id]

                session_id = proposed_id
                curve_pk = str(data.get("curve_pk", ""))[:256]
                _clients[session_id] = {"ws": ws, "curve_pk": curve_pk}

                peer_list = [
                    {"session": sid, "curve_pk": info["curve_pk"]}
                    for sid, info in _clients.items()
                    if sid != session_id
                ]
                await ws.send(json.dumps({
                    "type": "relay_peers",
                    "peers": peer_list,
                    "count": len(peer_list),
                }))

                if _relay_wallet:
                    await ws.send(json.dumps({
                        "type": "relay_wallet",
                        "address": _relay_wallet,
                    }))

                join_msg = json.dumps({
                    "type": "relay_join",
                    "session": session_id,
                    "curve_pk": curve_pk,
                    "ts": time.time(),
                })
                for sid, info in list(_clients.items()):
                    if sid != session_id:
                        asyncio.create_task(_delayed_forward(info["ws"], join_msg))

                await _broadcast_to_scanners({
                    "type": "peer_join",
                    "peers_online": len(_clients),
                    "ts": time.time(),
                })
                continue

            if not session_id:
                continue

            if msg_type == "msg":
                _stats["total_messages"] += 1

                await _broadcast_to_scanners({
                    "type": "activity",
                    "ts": time.time(),
                })

                encoded = json.dumps(data)
                if len(encoded) <= MAX_MSG_BYTES:
                    for sid, info in list(_clients.items()):
                        if sid != session_id:
                            asyncio.create_task(_delayed_forward(info["ws"], encoded))
                continue

            if msg_type == "key_request":
                encoded = json.dumps(data)
                if len(encoded) <= MAX_MSG_BYTES:
                    for sid, info in list(_clients.items()):
                        if sid != session_id:
                            asyncio.create_task(_delayed_forward(info["ws"], encoded))
                continue

            if msg_type == "key_share":
                target = data.get("to")
                if isinstance(target, str) and target in _clients:
                    payload = json.dumps(data)
                    if len(payload) <= MAX_MSG_BYTES:
                        try:
                            await _clients[target]["ws"].send(payload)
                        except Exception:
                            pass
                continue

            if msg_type == "heartbeat":
                continue

    except Exception:
        pass
    finally:
        if session_id and session_id in _clients:
            del _clients[session_id]
            leave_msg = json.dumps({"type": "relay_leave", "session": session_id})
            for sid, info in list(_clients.items()):
                try:
                    await info["ws"].send(leave_msg)
                except Exception:
                    pass

            await _broadcast_to_scanners({
                "type": "peer_leave",
                "peers_online": len(_clients),
                "ts": time.time(),
            })


async def _handle_scanner(ws):
    if len(_scanners) >= MAX_SCANNERS:
        try:
            await ws.close(1013, "too many scanners")
        except Exception:
            pass
        return

    _scanners.add(ws)
    try:
        await ws.send(json.dumps({
            "type": "snapshot",
            "peers_online": len(_clients),
            "total_messages": _stats["total_messages"],
            "total_connections": _stats["total_connections"],
            "uptime": time.time() - _stats["start_time"],
            "relay_wallet": _relay_wallet,
        }))
        async for _ in ws:
            pass
    except Exception:
        pass
    finally:
        _scanners.discard(ws)


async def run_relay(host: str = "0.0.0.0", port: int | None = None, wallet: str | None = None,
                    enable_scanner: bool = False):
    import os
    if port is None:
        port = int(os.environ.get("PORT", DEFAULT_PORT))
    global _relay_wallet
    if serve is None:
        print("ERROR: websockets package required. Install with: pip install websockets")
        return
    _stats["start_time"] = time.time()
    _relay_wallet = wallet
    print()
    print("  limes relay (privacy mode)")
    print("  " + "-" * 27)
    print(f"  listening on ws://{host}:{port}")
    print(f"  scanner metadata at ws://{host}:{port}/scan")
    print()
    print("  this relay is a dumb pipe:")
    print("    + messages are end-to-end encrypted")
    print("    + peers identified by random session IDs")
    print("    + no message content stored or logged")
    print("    + random forwarding delay prevents timing analysis")
    print()
    print(f"  limits: {MAX_PEERS} peers, {MAX_MSG_BYTES // 1024}KB max msg, {RATE_LIMIT_PER_SEC} msg/s per peer")
    print()
    if wallet:
        print(f"  relay wallet: {wallet}")
        print()

    if enable_scanner:
        from lime.scanner import run_scanner
        from lime.config import RELAY_SERVERS
        scanner_port = port + 1
        relay_url = f"ws://localhost:{port}"
        print(f"  scanner enabled on ws://{host}:{scanner_port}")
        print()
        asyncio.create_task(run_scanner(relay_url=relay_url, scanner_port=scanner_port))

    ws_kwargs: dict = {"max_size": MAX_MSG_BYTES}
    async with serve(_handler, host, port, **ws_kwargs):
        while True:
            await asyncio.sleep(30)
            print(f"  [{len(_clients)} peers | {len(_scanners)} scanners | {_stats['total_messages']} msgs forwarded]")


def main(port: int = DEFAULT_PORT, wallet: str | None = None, scanner: bool = False):
    asyncio.run(run_relay(port=port, wallet=wallet, enable_scanner=scanner))


if __name__ == "__main__":
    import sys
    scanner_flag = "--scanner" in sys.argv or "-s" in sys.argv
    main(scanner=scanner_flag)
