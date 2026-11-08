"""Configuration and workspace-safe paths."""
import os
from dataclasses import dataclass
from pathlib import Path

from .security import validate_model_name


@dataclass(frozen=True)
class Settings:
    """Runtime settings. All persistent data stays in the selected data directory."""

    data_dir: Path = Path.home() / ".ruller_ai"
    max_input_chars: int = 8_000
    max_memory_items: int = 2_000
    max_knowledge_items: int = 5_000
    provider: str | None = None
    model: str | None = None
    api_base: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        if self.provider is None and os.getenv("ULTRON_PROVIDER"):
            object.__setattr__(self, "provider", os.environ["ULTRON_PROVIDER"].strip())
        if self.model is None and os.getenv("ULTRON_MODEL"):
            object.__setattr__(self, "model", os.environ["ULTRON_MODEL"].strip())
        if self.api_base is None:
            value = os.getenv("OPENAI_API_BASE") or os.getenv("ULTRON_API_BASE")
            if value:
                object.__setattr__(self, "api_base", value.strip())
        if self.api_key is None:
            value = os.getenv("OPENAI_API_KEY") or os.getenv("ULTRON_API_KEY")
            if value:
                object.__setattr__(self, "api_key", value.strip())

        for name in ("max_input_chars", "max_memory_items", "max_knowledge_items"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        if self.max_input_chars > 100_000:
            raise ValueError("max_input_chars cannot exceed 100,000.")
        if self.provider is not None:
            if not isinstance(self.provider, str):
                raise ValueError("Provider name must be text.")
            provider = self.provider.strip().casefold()
            if provider not in {"", "offline", "none", "ollama", "local-ollama", "local_ollama",
                                "openai", "openai-compatible", "openai_compatible", "openai-compatible-http"}:
                raise ValueError("Unknown provider. Choose offline, ollama, or openai.")
            object.__setattr__(self, "provider", provider)
        if self.model is not None:
            try:
                object.__setattr__(self, "model", validate_model_name(self.model))
            except (AttributeError, ValueError) as exc:
                raise ValueError("Invalid model name.") from exc
        if self.api_base is not None and not isinstance(self.api_base, str):
            raise ValueError("API base URL must be text.")
        if self.api_key is not None:
            if not isinstance(self.api_key, str):
                raise ValueError("API key must be text.")
            key = self.api_key.strip()
            if len(key) > 4_096 or any(ch in key for ch in "\r\n\x00"):
                raise ValueError("API key contains invalid characters or exceeds the size limit.")
            object.__setattr__(self, "api_key", key or None)

    @property
    def memory_dir(self) -> Path:
        return self.data_dir / "memory"

    @property
    def memory_file(self) -> Path:
        return self.memory_dir / "conversation.json"

    @property
    def knowledge_file(self) -> Path:
        return self.data_dir / "knowledge.json"

    @property
    def feedback_file(self) -> Path:
        return self.data_dir / "feedback.jsonl"

    @property
    def guard_file(self) -> Path:
        return self.memory_dir / ".memory_guard.json"

    @property
    def backup_dir(self) -> Path:
        return self.memory_dir / "backup"
