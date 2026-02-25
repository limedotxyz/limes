"""
Ethereum wallet management and on-chain $LIME token interaction.

Generates a local wallet (private key stored in ~/.lime/wallet.json),
and submits PoW proofs to the LimeToken contract on Base to earn $LIME.
"""

import json
from pathlib import Path
from typing import Optional

from lime.config import CHAIN_ID, CHAIN_RPC, LIME_CONTRACT, LIME_DIR, WALLET_FILE

try:
    from web3 import Web3
    from eth_account import Account
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False

LIME_ABI = [
    {
        "inputs": [
            {"name": "payload", "type": "bytes"},
            {"name": "nonce", "type": "uint256"},
        ],
        "name": "mine",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "payload", "type": "bytes"},
            {"name": "nonce", "type": "uint256"},
            {"name": "relay", "type": "address"},
        ],
        "name": "mineWithRelay",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "registerRelay",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "relayMessageCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def generate_wallet() -> tuple[str, str]:
    """Generate a new Ethereum keypair. Returns (address, private_key_hex)."""
    if not HAS_WEB3:
        raise RuntimeError("web3 not installed")
    acct = Account.create()
    return acct.address, acct.key.hex()


def save_wallet(address: str, private_key: str):
    LIME_DIR.mkdir(parents=True, exist_ok=True)
    WALLET_FILE.write_text(json.dumps({
        "address": address,
        "private_key": private_key,
    }, indent=2))
    try:
        import os, stat
        os.chmod(WALLET_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def load_wallet() -> Optional[tuple[str, str]]:
    if not WALLET_FILE.exists():
        return None
    try:
        data = json.loads(WALLET_FILE.read_text())
        return data["address"], data["private_key"]
    except Exception:
        return None


def get_balance(address: str) -> Optional[float]:
    """Get $LIME balance for an address. Returns None if contract not deployed."""
    if not HAS_WEB3 or not LIME_CONTRACT:
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(CHAIN_RPC))
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(LIME_CONTRACT),
            abi=LIME_ABI,
        )
        raw = contract.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()
        return raw / 1e18
    except Exception:
        return None


def submit_proof(
    private_key: str,
    payload: bytes,
    nonce: int,
    relay_address: Optional[str] = None,
) -> Optional[str]:
    """
    Submit a PoW proof to the LimeToken contract.
    If relay_address is provided, uses mineWithRelay (90/10 split).
    Returns the transaction hash or None on failure.
    """
    if not HAS_WEB3 or not LIME_CONTRACT:
        return None

    try:
        w3 = Web3(Web3.HTTPProvider(CHAIN_RPC))
        acct = Account.from_key(private_key)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(LIME_CONTRACT),
            abi=LIME_ABI,
        )

        if relay_address:
            fn = contract.functions.mineWithRelay(
                payload, nonce, Web3.to_checksum_address(relay_address)
            )
        else:
            fn = contract.functions.mine(payload, nonce)

        tx = fn.build_transaction({
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gas": 150_000,
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID,
        })

        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
    except Exception:
        return None


def register_relay(private_key: str) -> Optional[str]:
    """Register as a relay operator on-chain. Returns tx hash or None."""
    if not HAS_WEB3 or not LIME_CONTRACT:
        return None

    try:
        w3 = Web3(Web3.HTTPProvider(CHAIN_RPC))
        acct = Account.from_key(private_key)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(LIME_CONTRACT),
            abi=LIME_ABI,
        )

        tx = contract.functions.registerRelay().build_transaction({
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gas": 100_000,
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID,
        })

        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
    except Exception:
        return None
