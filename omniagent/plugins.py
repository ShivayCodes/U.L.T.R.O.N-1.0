"""Plugin and skill registry for OmniAgent Studio."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class Skill:
    name: str
    description: str
    category: str = "core"
    input_schema: dict[str, str] = field(default_factory=dict)
    handler: Callable[..., str] | None = None

    def run(self, **kwargs: Any) -> str:
        if self.handler is None:
            raise ValueError(f"Skill '{self.name}' has no handler configured.")
        return self.handler(**kwargs)


class PluginRegistry:
    """Built-in and plugin-based execution registry."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self.register(
            Skill(
                name="code_review",
                description="Review the supplied code or issue description and suggest improvements.",
                category="coding",
                input_schema={"text": "code or issue description"},
                handler=lambda text: f"Code review: keep the architecture clear, enforce tests, and validate on local-only assumptions.\n\n{text[:500]}",
            )
        )
        self.register(
            Skill(
                name="summarize",
                description="Summarize text into structured bullet points.",
                category="knowledge",
                input_schema={"text": "long text"},
                handler=lambda text: "Summary:\n- Key point 1\n- Key point 2\n- Key point 3\n\nSource text:\n" + text[:600],
            )
        )
        self.register(
            Skill(
                name="video_gen",
                description="Create a script outline for a short-form video workflow.",
                category="media",
                input_schema={"topic": "video topic"},
                handler=lambda topic: f"Video generation plan for '{topic}': 1) write hook, 2) collect footage, 3) add voiceover, 4) render vertical MP4.",
            )
        )

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def list_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def run(self, name: str, **kwargs: Any) -> str:
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' is not registered.")
        return self._skills[name].run(**kwargs)
