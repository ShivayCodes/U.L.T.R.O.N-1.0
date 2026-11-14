"""Configuration and runtime settings for OmniAgent Studio."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Local-first configuration for the OmniAgent runtime."""

    project_name: str = "OmniAgent Studio"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".omniagent")
    sqlite_path: Path | None = None
    provider: str = "offline"
    model: str = "local-default"
    api_base: str | None = None
    api_key: str | None = None
    max_sessions: int = 50
    max_history: int = 250
    local_only: bool = True

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir).expanduser()
        if self.sqlite_path is None:
            self.sqlite_path = self.data_dir / "omniagent.db"
        else:
            self.sqlite_path = Path(self.sqlite_path).expanduser()

        self.provider = (os.getenv("OMNI_PROVIDER") or self.provider).strip() or "offline"
        self.model = (os.getenv("OMNI_MODEL") or self.model).strip() or "local-default"
        self.api_base = os.getenv("OMNI_API_BASE") or self.api_base
        self.api_key = os.getenv("OMNI_API_KEY") or self.api_key
        self.local_only = str(os.getenv("OMNI_LOCAL_ONLY", "true")).lower() not in {"0", "false", "no"}

    @property
    def sessions_path(self) -> Path:
        return self.data_dir / "sessions"

    @property
    def plugins_dir(self) -> Path:
        return self.data_dir / "plugins"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_path.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        if self.sqlite_path.parent:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
