"""Simple offline document store and transparent lexical retrieval."""
import re
from pathlib import Path
from typing import Any

from .storage import read_json, write_json

TOKEN_RE = re.compile(r"[a-zA-Z0-9_'-]+")


def tokens(text: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(text) if len(token) > 1}


class KnowledgeBase:
    SUPPORTED = {".txt", ".md", ".rst", ".py", ".json", ".csv", ".html", ".xml"}

    def __init__(self, path: Path, max_items: int = 5_000) -> None:
        self.path = path
        self.max_items = max(1, max_items)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[dict[str, Any]] = read_json(path, [])
        if not isinstance(self._items, list):
            raise RuntimeError(f"Invalid knowledge format in {path}; expected a JSON list.")

        # Keep a lightweight inverted index so repeated searches do not tokenize
        # every passage, and duplicate checks do not scan the whole collection.
        self._next_id = 0
        self._order: list[int] = []
        self._entries: dict[int, tuple[dict[str, Any], set[str]]] = {}
        self._postings: dict[str, set[int]] = {}
        self._fingerprint_counts: dict[tuple[Any, Any], int] = {}
        for item in self._items:
            self._index_item(item)

    @property
    def count(self) -> int:
        return len(self._items)

    def _index_item(self, item: dict[str, Any]) -> int:
        item_id = self._next_id
        self._next_id += 1
        item_tokens = tokens(str(item.get("text", "")))
        self._order.append(item_id)
        self._entries[item_id] = (item, item_tokens)
        for token in item_tokens:
            self._postings.setdefault(token, set()).add(item_id)
        fingerprint = (item.get("source"), item.get("text"))
        self._fingerprint_counts[fingerprint] = self._fingerprint_counts.get(fingerprint, 0) + 1
        return item_id

    def _remove_oldest(self) -> None:
        item_id = self._order.pop(0)
        item, item_tokens = self._entries.pop(item_id)
        for token in item_tokens:
            posting = self._postings[token]
            posting.remove(item_id)
            if not posting:
                del self._postings[token]
        fingerprint = (item.get("source"), item.get("text"))
        remaining = self._fingerprint_counts[fingerprint] - 1
        if remaining:
            self._fingerprint_counts[fingerprint] = remaining
        else:
            del self._fingerprint_counts[fingerprint]

    def add_text(self, text: str, source: str = "manual") -> bool:
        cleaned = text.strip()
        if not cleaned:
            return False
        record = {"text": cleaned[:20_000], "source": source[:500]}
        fingerprint = (record["source"], record["text"])
        if self._fingerprint_counts.get(fingerprint, 0):
            return False
        self._items.append(record)
        self._index_item(record)
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items :]
            self._remove_oldest()
        write_json(self.path, self._items)
        return True

    def ingest_file(self, path: Path) -> int:
        if path.suffix.casefold() not in self.SUPPORTED:
            raise ValueError(f"Unsupported file type: {path.suffix or '(no extension)'}")
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        if path.stat().st_size > 1_000_000:
            raise ValueError("Files larger than 1 MB are not accepted.")
        content = path.read_text(encoding="utf-8", errors="replace")
        chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", content) if chunk.strip()]
        added = sum(self.add_text(chunk, str(path)) for chunk in chunks)
        return added

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = tokens(query)
        if not query_tokens:
            return []

        # Accumulate overlap counts only for entries indexed under a query token.
        scores: dict[int, int] = {}
        for token in query_tokens:
            for item_id in self._postings.get(token, ()):
                scores[item_id] = scores.get(item_id, 0) + 1
        if not scores or limit <= 0:
            return []

        # IDs increase with insertion order, preserving the previous stable tie order.
        ranked_ids = sorted(scores, key=lambda item_id: (-scores[item_id], item_id))[:limit]
        query_size = len(query_tokens)
        return [
            {
                "score": round(scores[item_id] / query_size, 3),
                "text": self._entries[item_id][0]["text"],
                "source": self._entries[item_id][0].get("source", "unknown"),
            }
            for item_id in ranked_ids
        ]
