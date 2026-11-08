"""Configuration and workspace-safe paths."""
import os
from dataclasses import dataclass
from pathlib import Path


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
        if self.provider is None:
            env_provider = os.getenv("ULTRON_PROVIDER")
            if env_provider:
                object.__setattr__(self, "provider", env_provider.strip())
        if self.model is None:
            env_model = os.getenv("ULTRON_MODEL")
            if env_model:
                object.__setattr__(self, "model", env_model.strip())
        if self.api_base is None:
            env_api_base = os.getenv("OPENAI_API_BASE") or os.getenv("ULTRON_API_BASE")
            if env_api_base:
                object.__setattr__(self, "api_base", env_api_base.strip())
        if self.api_key is None:
            env_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ULTRON_API_KEY")
            if env_api_key:
                object.__setattr__(self, "api_key", env_api_key.strip())

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
