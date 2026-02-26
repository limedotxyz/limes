import hashlib
import json
import time
import uuid
from dataclasses import dataclass

from lime.config import MAX_MESSAGE_LENGTH, MESSAGE_TTL, POW_DIFFICULTY


@dataclass
class Message:
    id: str
    prev_hash: str
    author_name: str
    author_tag: str
    author_pubkey: str
    content: str
    content_type: str       # "text" | "code" | "file"
    timestamp: float
    ttl: int
    nonce: str
    pow_hash: str
    signature: str
    board: str = "general"
    thread_id: str = ""
    thread_title: str = ""
    reply_to: str = ""
    file_name: str = ""
    file_data: str = ""     # base64
    file_size: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.timestamp + self.ttl

    @property
    def remaining_seconds(self) -> int:
        return max(0, int((self.timestamp + self.ttl) - time.time()))

    @property
    def remaining_display(self) -> str:
        s = self.remaining_seconds
        return f"{s // 60}m" if s >= 60 else f"{s}s"

    @property
    def display_author(self) -> str:
        return f"{self.author_name}#{self.author_tag}"

    def pow_payload(self) -> bytes:
        """Canonical bytes fed into the PoW miner (excludes nonce, pow_hash, sig)."""
        return json.dumps({
            "id": self.id,
            "prev_hash": self.prev_hash,
            "author_name": self.author_name,
            "author_tag": self.author_tag,
            "author_pubkey": self.author_pubkey,
            "content": self.content,
            "content_type": self.content_type,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "board": self.board,
            "thread_id": self.thread_id,
            "thread_title": self.thread_title,
            "reply_to": self.reply_to,
        }, sort_keys=True).encode()

    def signable_payload(self) -> bytes:
        """Canonical bytes that get signed (everything except the signature)."""
        return json.dumps({
            "id": self.id,
            "prev_hash": self.prev_hash,
            "author_name": self.author_name,
            "author_tag": self.author_tag,
            "author_pubkey": self.author_pubkey,
            "content": self.content,
            "content_type": self.content_type,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "nonce": self.nonce,
            "pow_hash": self.pow_hash,
            "board": self.board,
            "thread_id": self.thread_id,
            "thread_title": self.thread_title,
            "reply_to": self.reply_to,
        }, sort_keys=True).encode()

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "prev_hash": self.prev_hash,
            "author_name": self.author_name,
            "author_tag": self.author_tag,
            "author_pubkey": self.author_pubkey,
            "content": self.content,
            "content_type": self.content_type,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "nonce": self.nonce,
            "pow_hash": self.pow_hash,
            "signature": self.signature,
            "board": self.board,
            "thread_id": self.thread_id,
            "thread_title": self.thread_title,
            "reply_to": self.reply_to,
        }
        if self.file_name:
            d["file_name"] = self.file_name
            d["file_data"] = self.file_data
            d["file_size"] = self.file_size
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(
            id=d["id"],
            prev_hash=d["prev_hash"],
            author_name=d["author_name"],
            author_tag=d["author_tag"],
            author_pubkey=d["author_pubkey"],
            content=d["content"],
            content_type=d["content_type"],
            timestamp=d["timestamp"],
            ttl=d["ttl"],
            nonce=d["nonce"],
            pow_hash=d["pow_hash"],
            signature=d["signature"],
            board=d.get("board", "general"),
            thread_id=d.get("thread_id", ""),
            thread_title=d.get("thread_title", ""),
            reply_to=d.get("reply_to", ""),
            file_name=d.get("file_name", ""),
            file_data=d.get("file_data", ""),
            file_size=d.get("file_size", 0),
        )

    @classmethod
    def from_json(cls, s: str) -> "Message":
        return cls.from_dict(json.loads(s))


# ---------------------------------------------------------------------------
# Proof of Work
# ---------------------------------------------------------------------------

def mine_pow(payload: bytes, difficulty: int = POW_DIFFICULTY) -> tuple[str, str]:
    """Hashcash-style PoW: find nonce where SHA-256(payload||nonce) < target."""
    target = 1 << (256 - difficulty)
    n = 0
    while True:
        nonce = n.to_bytes(8, "big")
        h = hashlib.sha256(payload + nonce).digest()
        if int.from_bytes(h, "big") < target:
            return nonce.hex(), h.hex()
        n += 1


def verify_pow(payload: bytes, nonce_hex: str, pow_hash_hex: str,
               difficulty: int = POW_DIFFICULTY) -> bool:
    nonce = bytes.fromhex(nonce_hex)
    h = hashlib.sha256(payload + nonce).digest()
    if h.hex() != pow_hash_hex:
        return False
    return int.from_bytes(h, "big") < (1 << (256 - difficulty))


# ---------------------------------------------------------------------------
# Message factory
# ---------------------------------------------------------------------------

def create_message(
    content: str,
    content_type: str,
    author_name: str,
    author_tag: str,
    author_pubkey_hex: str,
    prev_hash: str,
    sign_fn,                # (bytes) -> bytes
    *,
    board: str = "general",
    thread_id: str = "",
    thread_title: str = "",
    reply_to: str = "",
    file_name: str = "",
    file_data: str = "",
    file_size: int = 0,
) -> Message:
    if content_type != "file" and len(content) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message too long ({len(content)} > {MAX_MESSAGE_LENGTH})")

    msg = Message(
        id=str(uuid.uuid4()),
        prev_hash=prev_hash,
        author_name=author_name,
        author_tag=author_tag,
        author_pubkey=author_pubkey_hex,
        content=content,
        content_type=content_type,
        timestamp=time.time(),
        ttl=MESSAGE_TTL,
        nonce="",
        pow_hash="",
        signature="",
        board=board,
        thread_id=thread_id,
        thread_title=thread_title,
        reply_to=reply_to,
        file_name=file_name,
        file_data=file_data,
        file_size=file_size,
    )

    msg.nonce, msg.pow_hash = mine_pow(msg.pow_payload())

    sig_bytes = sign_fn(msg.signable_payload())
    msg.signature = sig_bytes.hex()

    return msg
