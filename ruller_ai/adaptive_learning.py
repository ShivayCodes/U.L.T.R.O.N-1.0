"""User-approved examples and feedback for bounded, transparent adaptation.

This stores retrieval/prompt examples; it does not train or modify model weights.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import read_json, write_json


class AdaptiveLearning:
    MAX_EXAMPLES = 200
    MAX_FEEDBACK = 100
    MAX_TEXT_CHARS = 4_000

    def __init__(self, path: Path) -> None:
        self.path = path
        raw = read_json(path, {})
        # Preserve the older autolearn-only settings format.
        self._data: dict[str, Any] = raw if isinstance(raw, dict) else {}
        self._data.setdefault("enabled", False)
        self._data.setdefault("examples", [])
        self._data.setdefault("feedback", [])
        if not isinstance(self._data["examples"], list):
            self._data["examples"] = []
        if not isinstance(self._data["feedback"], list):
            self._data["feedback"] = []

    @property
    def auto_learn_enabled(self) -> bool:
        return self._data.get("enabled") is True

    @property
    def example_count(self) -> int:
        return len(self._data["examples"])

    @property
    def feedback_count(self) -> int:
        return len(self._data["feedback"])

    def set_auto_learn(self, enabled: bool) -> None:
        self._data["enabled"] = enabled
        self._save()

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {part.casefold().strip(".,!?;:'\"()[]{}") for part in text.split() if len(part.strip(".,!?;:'\"()[]{}")) > 2}

    def teach(self, question: str, approved_answer: str) -> str:
        question, approved_answer = question.strip(), approved_answer.strip()
        if not question or not approved_answer:
            raise ValueError("Both a question and its approved answer are required.")
        if len(question) > self.MAX_TEXT_CHARS or len(approved_answer) > self.MAX_TEXT_CHARS:
            raise ValueError(f"Questions and answers must be {self.MAX_TEXT_CHARS} characters or shorter.")
        for item in self._data["examples"]:
            if item.get("question", "").casefold() == question.casefold():
                item["answer"] = approved_answer
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save()
                return str(item["id"])
        example_id = uuid.uuid4().hex[:10]
        self._data["examples"].append({
            "id": example_id,
            "question": question,
            "answer": approved_answer,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        self._data["examples"] = self._data["examples"][-self.MAX_EXAMPLES:]
        self._save()
        return example_id

    def matching_examples(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        query_terms = self._terms(query)
        if not query_terms:
            return []
        matches: list[tuple[float, int, dict[str, Any]]] = []
        for position, item in enumerate(self._data["examples"]):
            question = str(item.get("question", ""))
            terms = self._terms(question)
            overlap = len(query_terms & terms)
            if overlap:
                matches.append((overlap / len(query_terms), position, item))
        matches.sort(key=lambda hit: (-hit[0], hit[1]))
        return [dict(item) for _score, _position, item in matches[:limit]]

    def record_feedback(self, question: str, answer: str, rating: str, note: str = "") -> None:
        if rating not in {"helpful", "not-helpful"}:
            raise ValueError("Feedback rating must be helpful or not-helpful.")
        cleaned_note = note.strip()
        if len(cleaned_note) > self.MAX_TEXT_CHARS:
            raise ValueError(f"Feedback notes must be {self.MAX_TEXT_CHARS} characters or shorter.")
        self._data["feedback"].append({
            "rating": rating,
            "question": question.strip()[:self.MAX_TEXT_CHARS],
            # Keep only a short response excerpt; ratings are not training labels for model weights.
            "answer_excerpt": answer.strip()[:500],
            "note": cleaned_note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        self._data["feedback"] = self._data["feedback"][-self.MAX_FEEDBACK:]
        self._save()

    def recent_notes(self, limit: int = 3) -> list[str]:
        if limit <= 0:
            return []
        return [str(item.get("note", "")) for item in self._data["feedback"][-limit:] if item.get("note")]

    def clear(self) -> None:
        self._data["examples"] = []
        self._data["feedback"] = []
        self._save()

    def _save(self) -> None:
        write_json(self.path, self._data)
