"""
End-to-end encryption for lime relay communication.

Uses NaCl (PyNaCl) for:
- X25519 key exchange (Ed25519 -> Curve25519 conversion)
- SealedBox for room key distribution (asymmetric, no sender identity)
- SecretBox for message encryption (symmetric, fast)

The relay never sees plaintext messages — only encrypted blobs.
Peers derive the room key through an encrypted key exchange that
the relay cannot decrypt.
"""

import base64

from nacl.public import SealedBox, PublicKey as CurvePublicKey
from nacl.secret import SecretBox
from nacl.signing import SigningKey, VerifyKey
from nacl.utils import random as nacl_random

ROOM_KEY_SIZE = SecretBox.KEY_SIZE  # 32 bytes


def sign_curve_pk(signing_key: SigningKey, curve_pk_hex: str) -> str:
    """Sign the X25519 public key with Ed25519 to prevent MITM attacks."""
    sig = signing_key.sign(bytes.fromhex(curve_pk_hex)).signature
    return sig.hex()


def verify_curve_pk_sig(verify_key_hex: str, curve_pk_hex: str, sig_hex: str) -> bool:
    """Verify that a curve public key was signed by the claimed identity."""
    try:
        vk = VerifyKey(bytes.fromhex(verify_key_hex))
        vk.verify(bytes.fromhex(curve_pk_hex), bytes.fromhex(sig_hex))
        return True
    except Exception:
        return False


def generate_room_key() -> bytes:
    return nacl_random(ROOM_KEY_SIZE)


def signing_to_curve_private(signing_key: SigningKey):
    return signing_key.to_curve25519_private_key()


def verify_to_curve_public(verify_key: VerifyKey):
    return verify_key.to_curve25519_public_key()


def curve_public_from_hex(hex_str: str) -> CurvePublicKey:
    return CurvePublicKey(bytes.fromhex(hex_str))


def seal_room_key(room_key: bytes, recipient_curve_public) -> str:
    """Encrypt room key so only the recipient can open it. Returns base64."""
    sealed = SealedBox(recipient_curve_public).encrypt(room_key)
    return base64.b64encode(sealed).decode()


def unseal_room_key(sealed_b64: str, my_curve_private) -> bytes:
    """Decrypt room key using our X25519 private key."""
    sealed = base64.b64decode(sealed_b64)
    return SealedBox(my_curve_private).decrypt(sealed)


def encrypt_message(plaintext: bytes, room_key: bytes) -> str:
    """Encrypt message bytes with the room key. Returns base64."""
    return base64.b64encode(SecretBox(room_key).encrypt(plaintext)).decode()


def decrypt_message(ciphertext_b64: str, room_key: bytes) -> bytes:
    """Decrypt a base64 envelope back to plaintext bytes."""
    return SecretBox(room_key).decrypt(base64.b64decode(ciphertext_b64))
