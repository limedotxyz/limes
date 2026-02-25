import threading
from typing import Callable

from lime.message import Message


class MessageStore:
    def __init__(self):
        self._messages: dict[str, Message] = {}
        self._lock = threading.Lock()
        self._on_new: list[Callable[[Message], None]] = []
        self._last_hash = "0" * 64

    @property
    def last_hash(self) -> str:
        with self._lock:
            return self._last_hash

    def add(self, msg: Message) -> bool:
        """Add a message. Returns True if it was new (not dup, not expired)."""
        if msg.is_expired:
            return False
        with self._lock:
            if msg.id in self._messages:
                return False
            self._messages[msg.id] = msg
            self._last_hash = msg.pow_hash
        for cb in self._on_new:
            try:
                cb(msg)
            except Exception:
                pass
        return True

    def get_all(self) -> list[Message]:
        with self._lock:
            self._prune()
            return sorted(self._messages.values(), key=lambda m: m.timestamp)

    def get_by_board(self, board: str) -> list[Message]:
        with self._lock:
            self._prune()
            return sorted(
                [m for m in self._messages.values() if m.board == board],
                key=lambda m: m.timestamp,
            )

    def get_by_thread(self, thread_id: str) -> list[Message]:
        with self._lock:
            self._prune()
            return sorted(
                [m for m in self._messages.values() if m.thread_id == thread_id],
                key=lambda m: m.timestamp,
            )

    def get_threads(self, board: str) -> list[dict]:
        """Active threads in a board, sorted by latest activity (newest first)."""
        with self._lock:
            self._prune()
            threads: dict[str, dict] = {}
            for msg in self._messages.values():
                if msg.board != board or not msg.thread_id:
                    continue
                tid = msg.thread_id
                if tid not in threads:
                    threads[tid] = {
                        "thread_id": tid,
                        "title": msg.thread_title or "untitled",
                        "count": 0,
                        "latest": 0.0,
                        "preview": "",
                        "preview_author": "",
                    }
                t = threads[tid]
                t["count"] += 1
                if msg.thread_title:
                    t["title"] = msg.thread_title
                if msg.timestamp > t["latest"]:
                    t["latest"] = msg.timestamp
                    t["preview"] = msg.content[:60]
                    t["preview_author"] = msg.display_author
            return sorted(threads.values(), key=lambda x: x["latest"], reverse=True)

    def get_board_chat(self, board: str) -> list[Message]:
        """Board-level messages (no thread) — the general chat."""
        with self._lock:
            self._prune()
            return sorted(
                [m for m in self._messages.values() if m.board == board and not m.thread_id],
                key=lambda m: m.timestamp,
            )

    def get_boards(self) -> list[str]:
        with self._lock:
            boards = {m.board for m in self._messages.values() if not m.is_expired}
        return sorted(boards) if boards else ["general"]

    def get_mentions(self, name: str) -> list[Message]:
        tag = f"@{name}"
        return [m for m in self.get_all() if tag in m.content]

    def on_new_message(self, callback: Callable[[Message], None]):
        self._on_new.append(callback)

    def count(self) -> int:
        with self._lock:
            return len(self._messages)

    def has(self, msg_id: str) -> bool:
        with self._lock:
            return msg_id in self._messages

    def prune(self) -> int:
        with self._lock:
            return self._prune()

    def _prune(self) -> int:
        expired = [mid for mid, m in self._messages.items() if m.is_expired]
        for mid in expired:
            del self._messages[mid]
        return len(expired)
