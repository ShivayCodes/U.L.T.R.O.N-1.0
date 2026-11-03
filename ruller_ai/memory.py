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

        self._verify_guard()

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
        except (OSError, RuntimeError, ValueError) as exc:
            self._backup_memory("invalid-guard")
            raise RuntimeError(
                "Memory integrity check failed. The protection guard is unreadable; "
                "a backup was created and the session was stopped."
            ) from exc

        expected = guard.get("expected_hash") if isinstance(guard, dict) else None
        actual = self._fingerprint(self._items)
        if not isinstance(expected, str) or expected != actual:
            self._backup_memory("tamper")
            raise RuntimeError(
                "Memory integrity check failed. Protected memory or its guard was tampered with; "
                "a backup was created and the session was stopped."
            )

    def add(self, role: str, content: str) -> None:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("role must be user, assistant, or system")
        item = {
            "role": role,
            "content": content[:8_000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._items.append(item)
        self._items = self._items[-self.max_items :]
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
        self._items.append(item)
        self._items = self._items[-self.max_items :]
        write_json(self.path, self._items)
        self._write_guard()

    def recent(self, limit: int = 8) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items[-max(0, limit) :]]

    def clear(self) -> None:
        self._items = []
        write_json(self.path, self._items)
        self._write_guard()

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        terms = {term.casefold() for term in query.split() if len(term) > 2}
        if not terms:
            return []
        ranked = []
        for item in self._items:
            content = str(item.get("content", ""))
            words = set(content.casefold().split())
            score = len(terms & words)
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [dict(item) for _, item in ranked[:limit]]
