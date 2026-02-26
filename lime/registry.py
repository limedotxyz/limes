"""
On-chain relay discovery via the LimesRegistry contract on Base L2.
Falls back to hardcoded RELAY_SERVERS if the contract call fails or returns empty.
Caches the relay list for 5 minutes.
"""

import json
import time
from typing import Optional

from lime.config import CHAIN_RPC, REGISTRY_CONTRACT, RELAY_SERVERS

REGISTRY_ABI = json.loads('[{"inputs":[],"name":"getRelays","outputs":[{"components":[{"internalType":"address","name":"operator","type":"address"},{"internalType":"string","name":"url","type":"string"},{"internalType":"uint256","name":"registeredAt","type":"uint256"}],"internalType":"struct LimesRegistry.Relay[]","name":"","type":"tuple[]"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"relayCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]')

_cache: Optional[list[dict]] = None
_cache_time: float = 0.0
CACHE_TTL = 300  # 5 minutes


def fetch_relays_from_chain() -> list[dict]:
    """Fetch relay list from LimesRegistry contract. Returns list of {operator, url, registeredAt}."""
    global _cache, _cache_time

    if _cache is not None and time.time() - _cache_time < CACHE_TTL:
        return _cache

    if not REGISTRY_CONTRACT:
        return []

    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(CHAIN_RPC))
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(REGISTRY_CONTRACT),
            abi=REGISTRY_ABI,
        )
        raw = contract.functions.getRelays().call()
        relays = [
            {"operator": r[0], "url": r[1], "registeredAt": r[2]}
            for r in raw
        ]
        _cache = relays
        _cache_time = time.time()
        return relays
    except Exception:
        return []


def get_relay_urls() -> list[str]:
    """Get relay WebSocket URLs, preferring on-chain registry with hardcoded fallback."""
    chain_relays = fetch_relays_from_chain()
    if chain_relays:
        urls = [r["url"] for r in chain_relays if r.get("url")]
        if urls:
            return urls
    return list(RELAY_SERVERS)


def get_relays_with_info() -> list[dict]:
    """Get full relay info (for the scanner UI). Falls back to hardcoded with minimal info."""
    chain_relays = fetch_relays_from_chain()
    if chain_relays:
        return chain_relays
    return [{"operator": "", "url": url, "registeredAt": 0} for url in RELAY_SERVERS]
