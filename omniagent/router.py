"""Router that decides whether a user request requires chat, tools, or a plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RoutingDecision:
    route: str
    confidence: float
    rationale: str


class RequestRouter:
    """Heuristic router for the MVP. It keeps the logic transparent and local."""

    def route(self, user_message: str, *, context: dict[str, Any] | None = None) -> RoutingDecision:
        text = (user_message or "").strip().lower()
        context = context or {}
        if not text:
            return RoutingDecision("chat", 0.0, "Empty request")

        keywords = {
            "tool": {"run", "execute", "command", "terminal", "shell", "script", "search", "fetch", "read"},
            "plan": {"plan", "roadmap", "workflow", "steps", "build", "implement", "design"},
            "coding": {"fix", "debug", "code", "patch", "test", "refactor", "bug"},
            "media": {"video", "image", "audio", "tts", "render", "caption"},
        }

        scores = {name: sum(1 for keyword in words if keyword in text) for name, words in keywords.items()}
        best = max(scores.items(), key=lambda item: item[1], default=("chat", 0))

        if best[1] > 0:
            if best[0] == "tool":
                return RoutingDecision("tool", min(1.0, 0.55 + best[1] * 0.15), "Request contains action-oriented execution keywords.")
            if best[0] == "plan":
                return RoutingDecision("plan", min(1.0, 0.6 + best[1] * 0.15), "Request appears to need multi-step orchestration.")
            if best[0] == "coding":
                return RoutingDecision("tool", 0.8, "Request looks like code generation or fix execution.")
            if best[0] == "media":
                return RoutingDecision("tool", 0.8, "Request matches a media workflow.")

        return RoutingDecision("chat", 0.5, "No explicit tool or plan signal detected; default to conversational flow.")

    def build_plan(self, user_message: str) -> list[str]:
        text = (user_message or "").strip()
        if not text:
            return []
        return [
            "Clarify objective and constraints",
            "Inspect resources and local context",
            "Draft the execution path",
            "Run the relevant tool or workflow",
            "Verify output and summarize",
        ]
