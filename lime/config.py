from pathlib import Path

VERSION = "1.0.0"

LIME_DIR = Path.home() / ".lime"
IDENTITY_FILE = LIME_DIR / "identity.json"
PEERS_FILE = LIME_DIR / "peers.json"
WALLET_FILE = LIME_DIR / "wallet.json"

MULTICAST_GROUP = "239.42.42.42"
MULTICAST_PORT = 4200
TCP_PORT_DEFAULT = 4201

MESSAGE_TTL = 1440          # 24 minutes in seconds
MAX_MESSAGE_LENGTH = 4096
POW_DIFFICULTY = 20         # SHA-256 leading zero bits (~1s per message)

HEARTBEAT_INTERVAL = 30     # seconds between heartbeats
PEER_TIMEOUT = 90           # drop peer after this many seconds of silence
PRUNE_INTERVAL = 10         # seconds between expired-message sweeps

# Relay servers — peers connect here to find each other through NATs.
# Anyone can run a relay with `lime relay`. Add your relay URL here.
RELAY_SERVERS = [
    "wss://relay-production-e4f7.up.railway.app",
]

# Direct-connect bootstrap peers (IP:port of known nodes)
BOOTSTRAP_PEERS: list[tuple[str, int]] = []

# Auto-update URL — points to GitHub Releases
UPDATE_BASE_URL = "https://github.com/limedotxyz/limes/releases/latest/download"

# Scanner port for the limescan web server
SCANNER_PORT = 4211

# SOCKS5 proxy for Tor/VPN — set to e.g. "socks5://127.0.0.1:9050" for Tor
SOCKS_PROXY = ""

# Base L2 chain config for $LIME token rewards
CHAIN_RPC = "https://mainnet.base.org"
CHAIN_ID = 8453
LIME_CONTRACT = ""   # Clanker-deployed $LIME ERC-20 address
VAULT_CONTRACT = ""  # LimesVault staking/rewards contract address
