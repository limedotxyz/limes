import argparse
import asyncio
import curses
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from lime.config import (
    BOOTSTRAP_PEERS,
    IDENTITY_FILE,
    LIME_DIR,
    PEERS_FILE,
    TCP_PORT_DEFAULT,
    UPDATE_BASE_URL,
    VERSION,
)
from lime.crypto import (
    generate_keypair,
    load_identity,
    pubkey_tag,
    save_identity,
    sign,
)
from lime.message import create_message
from lime.network import Network
from lime.store import MessageStore
from lime.tui import LimeTUI
from lime.wallet import generate_wallet, load_wallet, save_wallet, get_balance, HAS_WEB3


# ------------------------------------------------------------------
# Pretty CLI helpers
# ------------------------------------------------------------------

def _step(num: int, total: int, msg: str):
    print(f"  [{num}/{total}] {msg}")


def _ok(msg: str):
    print(f"       {msg}")


def _fail(msg: str):
    print(f"       ERROR: {msg}")


# ------------------------------------------------------------------
# Install lime to PATH
# ------------------------------------------------------------------

def _install_to_path():
    """Copy the running exe to a directory on PATH so 'lime' works globally."""
    if not getattr(sys, "frozen", False):
        return

    exe_src = sys.executable
    install_dir = Path.home() / "AppData" / "Local" / "Programs" / "limes"
    install_dir.mkdir(parents=True, exist_ok=True)
    dest = install_dir / "limes.exe"

    copied = False
    if not (dest.exists() and dest.resolve() == Path(exe_src).resolve()):
        try:
            shutil.copy2(exe_src, dest)
            copied = True
        except Exception:
            pass

    dir_str = str(install_dir)
    try:
        user_path = subprocess.run(
            ["powershell", "-Command",
             "[Environment]::GetEnvironmentVariable('Path','User')"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if dir_str.lower() not in user_path.lower():
            new_path = user_path.rstrip(";") + ";" + dir_str
            subprocess.run(
                ["powershell", "-Command",
                 f"[Environment]::SetEnvironmentVariable('Path','{new_path}','User')"],
                capture_output=True, timeout=10,
            )
    except Exception:
        pass

    if copied:
        _ok(f'installed to {dest}')
        _ok('"limes" will work from any new terminal.')


# ------------------------------------------------------------------
# Self-upgrade
# ------------------------------------------------------------------

def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.strip().split("."))


def _cmd_upgrade():
    import tempfile
    from urllib.request import urlopen, Request
    from urllib.error import URLError

    print()
    print(f"  limes upgrade  (current: {VERSION})")
    print("  -------------")
    print()

    version_url = f"{UPDATE_BASE_URL}/version.txt"
    exe_url = f"{UPDATE_BASE_URL}/limes.exe"

    _ok("checking for updates...")
    try:
        req = Request(version_url, headers={"User-Agent": "lime-updater"})
        with urlopen(req, timeout=10) as resp:
            remote_version = resp.read().decode().strip()
    except (URLError, OSError) as exc:
        _fail(f"could not reach update server: {exc}")
        return

    try:
        if _parse_version(remote_version) <= _parse_version(VERSION):
            _ok(f"already up to date (v{VERSION}).")
            return
    except ValueError:
        _fail(f"bad version format from server: {remote_version!r}")
        return

    _ok(f"new version available: {remote_version}")

    if not getattr(sys, "frozen", False):
        _ok("not running as exe — upgrade only works for the packaged .exe")
        _ok(f"download manually from: {exe_url}")
        return

    install_dir = Path.home() / "AppData" / "Local" / "Programs" / "limes"
    current_exe = install_dir / "limes.exe"
    if not current_exe.exists():
        current_exe = Path(sys.executable)

    _ok(f"downloading v{remote_version}...")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".exe", prefix="lime_update_")
    try:
        req = Request(exe_url, headers={"User-Agent": "lime-updater"})
        with urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with os.fdopen(tmp_fd, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded / total * 100)
                        print(f"\r       downloading... {pct}%", end="", flush=True)
            print()
    except (URLError, OSError) as exc:
        _fail(f"download failed: {exc}")
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return

    _ok("installing update...")
    bat_path = Path(tempfile.gettempdir()) / "limes_update.bat"
    bat_content = f"""@echo off
ping 127.0.0.1 -n 2 > nul
copy /y "{tmp_path}" "{current_exe}" > nul
del "{tmp_path}" > nul 2>&1
echo.
echo   limes updated to v{remote_version}
echo   run "limes" to start.
echo.
del "%~f0" > nul 2>&1
"""
    bat_path.write_text(bat_content)
    subprocess.Popen(
        ["cmd", "/c", str(bat_path)],
        creationflags=0x00000010,
    )
    _ok(f"update will complete momentarily. close this window if it doesn't exit.")
    sys.exit(0)


# ------------------------------------------------------------------
# Windows Firewall
# ------------------------------------------------------------------

def _ensure_firewall_rule():
    """Add a Windows Firewall rule to allow lime TCP traffic."""
    rule_name = "limes P2P"
    try:
        check = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"],
            capture_output=True, text=True, timeout=10,
        )
        if check.returncode == 0 and rule_name in check.stdout:
            _ok("firewall rule exists.")
            return
    except Exception:
        pass

    _ok("adding firewall rule for lime...")
    for direction in ("in", "out"):
        try:
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={rule_name}", f"dir={direction}", "action=allow",
                 "protocol=TCP", f"localport={TCP_PORT_DEFAULT}",
                 "profile=any"],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass
    _ok("firewall configured.")


# ------------------------------------------------------------------
# Setup wizard
# ------------------------------------------------------------------

def _cmd_setup(then_open: bool = False):
    print()
    print("  limes setup")
    print("  -----------")
    print()
    total = 5

    # -- 1. Identity --
    _step(1, total, "setting up identity...")
    existing = load_identity()
    if existing:
        name, sk = existing
        tag = pubkey_tag(sk.verify_key)
        _ok(f"already set up as {name}#{tag}")
    else:
        print()
        name = input("       pick a name: ").strip()
        while not name or len(name) > 20 or " " in name:
            name = input("       name (1-20 chars, no spaces): ").strip()
        sk, vk = generate_keypair()
        save_identity(name, sk)
        tag = pubkey_tag(vk)
        _ok(f"identity saved as {name}#{tag}")

    # -- 2. Wallet --
    _step(2, total, "setting up wallet...")
    w = load_wallet()
    if w:
        _ok(f"wallet: {w[0]}")
    elif HAS_WEB3:
        addr, pk = generate_wallet()
        save_wallet(addr, pk)
        _ok(f"wallet created: {addr}")
        _ok("earn $LIME by sending messages (PoW rewards).")
    else:
        _ok("web3 not available — wallet skipped.")

    # -- 3. Firewall rule --
    _step(3, total, "configuring firewall...")
    _ensure_firewall_rule()

    # -- 4. Install to PATH --
    _step(4, total, "installing lime command...")
    _install_to_path()

    # -- 5. Done --
    _step(5, total, "setup complete!")
    print()
    print("       limes connects to relay servers automatically.")
    print("       peers on your LAN are discovered via multicast.")
    print()
    if then_open:
        print('  opening lime...')
        print()
    else:
        print('  run "limes" to start.')
        print()
    return True


# ------------------------------------------------------------------
# Identity helpers
# ------------------------------------------------------------------

def _setup_identity():
    result = load_identity()
    if result:
        name, sk = result
        vk = sk.verify_key
        tag = pubkey_tag(vk)
        return name, sk, vk, tag

    print("Welcome to limes.\n")
    name = input("Pick a name: ").strip()
    while not name or len(name) > 20 or " " in name:
        name = input("Name (1-20 chars, no spaces): ").strip()

    sk, vk = generate_keypair()
    save_identity(name, sk)
    tag = pubkey_tag(vk)
    print(f"\nIdentity saved as {name}#{tag}\n")
    return name, sk, vk, tag


# ------------------------------------------------------------------
# Saved peers
# ------------------------------------------------------------------

def _load_peers() -> list[list]:
    if PEERS_FILE.exists():
        try:
            return json.loads(PEERS_FILE.read_text())
        except Exception:
            return []
    return []


def _save_peer(host: str, port: int):
    peers = _load_peers()
    entry = [host, port]
    if entry not in peers:
        peers.append(entry)
        LIME_DIR.mkdir(parents=True, exist_ok=True)
        PEERS_FILE.write_text(json.dumps(peers, indent=2))


# ------------------------------------------------------------------
# Network thread (asyncio event loop)
# ------------------------------------------------------------------

_net_loop: asyncio.AbstractEventLoop | None = None


def _network_main(network: Network, saved_peers: list, connect_addr):
    global _net_loop
    _net_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_net_loop)

    async def _run():
        await network.start()
        await asyncio.sleep(0.5)

        for host, port in BOOTSTRAP_PEERS:
            asyncio.create_task(network.connect_to(host, port))

        for host, port in saved_peers:
            asyncio.create_task(network.connect_to(host, port))

        if connect_addr:
            asyncio.create_task(network.connect_to(connect_addr[0], connect_addr[1]))

        while network._running:
            await asyncio.sleep(1)

    _net_loop.run_until_complete(_run())


# ------------------------------------------------------------------
# Callbacks from TUI -> network
# ------------------------------------------------------------------

def _make_send_cb(network, store, name, tag, pubkey_hex, sk, ui_queue):
    def send(content: str, content_type: str, board: str = "general",
             thread_id: str = "", thread_title: str = "", reply_to: str = ""):
        async def _do():
            loop = asyncio.get_event_loop()
            msg = await loop.run_in_executor(
                None,
                lambda: create_message(
                    content, content_type, name, tag, pubkey_hex,
                    store.last_hash, lambda data: sign(sk, data),
                    board=board, thread_id=thread_id,
                    thread_title=thread_title, reply_to=reply_to,
                ),
            )
            store.add(msg)
            await network.broadcast(msg)
            ui_queue.put(("msg_sent", msg))

        if _net_loop:
            asyncio.run_coroutine_threadsafe(_do(), _net_loop)

    return send


def _make_connect_cb(network):
    def connect(host: str, port: int):
        _save_peer(host, port)
        if _net_loop:
            asyncio.run_coroutine_threadsafe(network.connect_to(host, port), _net_loop)

    return connect


# ------------------------------------------------------------------
# Open the TUI
# ------------------------------------------------------------------

def _open_tui(args):
    name, sk, vk, tag = _setup_identity()
    pubkey_hex = vk.encode().hex()

    ui_queue: queue.Queue = queue.Queue()
    store = MessageStore()

    network = Network(
        name=name, tag=tag, pubkey_hex=pubkey_hex,
        signing_key=sk, store=store, ui_queue=ui_queue,
        tcp_port=args.port,
    )

    connect_addr = None
    if args.command == "connect" and args.address:
        parts = args.address.rsplit(":", 1)
        if len(parts) == 2:
            connect_addr = (parts[0], int(parts[1]))
            _save_peer(parts[0], int(parts[1]))

    saved_peers = _load_peers()

    net_thread = threading.Thread(
        target=_network_main,
        args=(network, saved_peers, connect_addr),
        daemon=True,
    )
    net_thread.start()

    tui = LimeTUI(
        name=name,
        tag=tag,
        store=store,
        ui_queue=ui_queue,
        send_cb=_make_send_cb(network, store, name, tag, pubkey_hex, sk, ui_queue),
        connect_cb=_make_connect_cb(network),
    )

    curses.wrapper(tui.run)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="limes",
        description="limes \u2014 anonymous ephemeral broadcast network",
    )
    parser.add_argument("-v", "--version", action="version", version=f"limes {VERSION}")
    parser.add_argument("command", nargs="?", default=None,
                        help="setup | connect <addr> | peers | reset | upgrade | relay | wallet")
    parser.add_argument("address", nargs="?", default=None)
    parser.add_argument("-p", "--port", type=int, default=TCP_PORT_DEFAULT,
                        help="TCP listen port")
    parser.add_argument("--export", action="store_true",
                        help="show private key (use with 'wallet')")

    args = parser.parse_args()

    if getattr(sys, "frozen", False):
        _install_to_path()

    if args.command == "upgrade":
        _cmd_upgrade()
        return

    if args.command == "relay":
        from lime.relay import main as relay_main
        relay_port = int(args.address) if args.address else 4210
        w = load_wallet()
        relay_wallet = w[0] if w else None
        relay_main(port=relay_port, wallet=relay_wallet, scanner=True)
        return

    if args.command == "scanner":
        print()
        print("  scanner is now built into 'limes relay'.")
        print("  just run: limes relay")
        print()
        return

    if args.command == "setup":
        _cmd_setup()
        return

    if args.command == "reset":
        if IDENTITY_FILE.exists():
            IDENTITY_FILE.unlink()
            print("Identity reset.")
        else:
            print("No identity to reset.")
        return

    if args.command == "peers":
        peers = _load_peers()
        if not peers:
            print("No saved peers.")
        for h, p in peers:
            print(f"  {h}:{p}")
        return

    if args.command == "wallet":
        w = load_wallet()
        if not w:
            print("No wallet. Run 'limes setup' first.")
            return
        addr, pk = w
        print(f"  address: {addr}")
        bal = get_balance(addr)
        if bal is not None:
            print(f"  $LIME:   {bal:.2f}")
        else:
            print("  $LIME:   contract not deployed yet")
        if args.export:
            print()
            print("  WARNING: never share your private key with anyone.")
            print(f"  private key: {pk}")
        else:
            print()
            print("  run 'limes wallet --export' to reveal your private key.")
        return

    if not load_identity():
        ok = _cmd_setup(then_open=True)
        if not ok:
            return

    _open_tui(args)


if __name__ == "__main__":
    main()
