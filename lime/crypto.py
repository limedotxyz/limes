import json

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey, VerifyKey

from lime.config import IDENTITY_FILE, LIME_DIR


def generate_keypair() -> tuple[SigningKey, VerifyKey]:
    sk = SigningKey.generate()
    return sk, sk.verify_key


def pubkey_tag(verify_key: VerifyKey) -> str:
    """First 4 hex chars of the public key — used as a short visual tag."""
    return verify_key.encode().hex()[:4]


def save_identity(name: str, signing_key: SigningKey):
    LIME_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "name": name,
        "signing_key_hex": signing_key.encode(encoder=HexEncoder).decode(),
    }
    IDENTITY_FILE.write_text(json.dumps(data, indent=2))
    try:
        import os, stat
        os.chmod(IDENTITY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def load_identity() -> tuple[str, SigningKey] | None:
    if not IDENTITY_FILE.exists():
        return None
    try:
        data = json.loads(IDENTITY_FILE.read_text())
        sk = SigningKey(data["signing_key_hex"], encoder=HexEncoder)
        return data["name"], sk
    except Exception:
        return None


def sign(signing_key: SigningKey, data: bytes) -> bytes:
    return signing_key.sign(data).signature


def verify(pubkey_hex: str, signature_hex: str, data: bytes) -> bool:
    try:
        vk = VerifyKey(bytes.fromhex(pubkey_hex))
        vk.verify(data, bytes.fromhex(signature_hex))
        return True
    except Exception:
        return False
