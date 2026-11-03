"""Protected memory storage with automatic learning support."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import read_json, write_json


class MemoryStore:
    """Local memory with tamper detection and durable persistence."""

    def __init__(self, path: Path, max_items: int = 2_000, guard_path: Path | None = None) -> None:
        self.path = path
        self.max_items = max(1, max_items)
        self.guard_path = guard_path or path.parent / ".memory_guard.json"
        self.backup_dir = path.parent / "backup"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._items: list[dict[str, Any]] = read_json(path, [])
        if not isinstance(self._items, list):
            raise RuntimeError(f"Invalid memory format in {path}; expected a JSON list.")
        self._build_search_index()

        self._verify_guard()

    def _build_search_index(self) -> None:
        self._next_id = 0
        self._order: list[int] = []
        self._entries: dict[int, tuple[dict[str, Any], set[str]]] = {}
        self._postings: dict[str, set[int]] = {}
        for item in self._items:
            self._index_item(item)

    def _index_item(self, item: dict[str, Any]) -> None:
        item_id = self._next_id
        self._next_id += 1
        content = str(item.get("content", ""))
        words = {word for word in content.casefold().split() if len(word) > 2}
        self._order.append(item_id)
        self._entries[item_id] = (item, words)
        for word in words:
            self._postings.setdefault(word, set()).add(item_id)

    def _remove_oldest_indexed_item(self) -> None:
        item_id = self._order.pop(0)
        _, words = self._entries.pop(item_id)
        for word in words:
            posting = self._postings[word]
            posting.remove(item_id)
            if not posting:
                del self._postings[word]

    def _append(self, item: dict[str, Any]) -> None:
        self._items.append(item)
        self._index_item(item)
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items :]
            self._remove_oldest_indexed_item()

    def _fingerprint(self, payload: Any) -> str:
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def _backup_memory(self, reason: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.backup_dir / f"memory-backup-{reason}-{timestamp}.json"
        write_json(backup_path, self._items)

    def _write_guard(self) -> None:
        payload = {
            "expected_hash": self._fingerprint(self._items),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
        }
        write_json(self.guard_path, payload)

    def _verify_guard(self) -> None:
        if not self.guard_path.exists():
            self._write_guard()
            return

        try:
            guard = read_json(self.guard_path, {})
        except RuntimeError as exc:
            raise RuntimeError(
                f"Memory integrity guard is invalid: {self.guard_path}"
            ) from exc

        if not isinstance(guard, dict) or not isinstance(guard.get("expected_hash"), str):
            raise RuntimeError(f"Memory integrity guard is invalid: {self.guard_path}")
        expected = guard.get("expected_hash")
        actual = self._fingerprint(self._items)
        if expected != actual:
            self._backup_memory("tamper")
            raise RuntimeError(
                "Memory integrity check failed. Protected memory was tampered with; "
                "a backup was created and the session was stopped."
            )
        self._write_guard()

    def add(self, role: str, content: str) -> None:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("role must be user, assistant, or system")
        item = {
            "role": role,
            "content": content[:8_000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._append(item)
        write_json(self.path, self._items)
        self._write_guard()

    def add_auto_memory(self, source: str, content: str) -> None:
        cleaned = content.strip()
        if not cleaned:
            return
        item = {
            "role": "system",
            "content": f"[auto-learn:{source}] {cleaned}",
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._append(item)
        write_json(self.path, self._items)
        self._write_guard()

    def recent(self, limit: int = 8) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items[-max(0, limit) :]]

    def clear(self) -> None:
        self._items = []
        self._build_search_index()
        write_json(self.path, self._items)
        self._write_guard()

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        terms = {term.casefold() for term in query.split() if len(term) > 2}
        if not terms or limit <= 0:
            return []
        scores: dict[int, int] = {}
        for term in terms:
            for item_id in self._postings.get(term, ()):
                scores[item_id] = scores.get(item_id, 0) + 1
        ranked_ids = sorted(scores, key=lambda item_id: (-scores[item_id], item_id))[:limit]
        return [dict(self._entries[item_id][0]) for item_id in ranked_ids]
