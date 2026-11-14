"""Provider abstractions and local-first generation support."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ProviderError(RuntimeError):
    """Raised when provider configuration or execution fails."""


class OfflineProvider:
    name = "offline"

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        del max_tokens
        system_text = system_prompt or "You are OmniAgent Studio."
        return (
            f"{system_text}\n\n"
            f"Local-only mode is active. No external provider call was made.\n\n"
            f"User request: {prompt}"
        )


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = "llama3.1", api_base: str | None = None, api_key: str | None = None) -> None:
        self.model = model
        self.api_base = api_base or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.api_key = api_key

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        if not self.api_base:
            raise ProviderError("Ollama base URL is not configured.")
        payload = {
            "model": self.model,
            "prompt": (system_prompt + "\n\n" if system_prompt else "") + prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        request = urllib.request.Request(
            urllib.parse.urljoin(self.api_base.rstrip("/") + "/", "api/generate"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc
        text = body.get("response") if isinstance(body, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise ProviderError("Ollama returned an empty response.")
        return text.strip()


class OpenAICompatibleProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_base: str | None = None, api_key: str | None = None) -> None:
        self.model = model
        self.api_base = (api_base or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not configured.")
        payload = {
            "model": self.model,
            "messages": [],
            "max_tokens": max_tokens,
        }
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        request = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise ProviderError(f"OpenAI-compatible request failed: {exc}") from exc
        choices = body.get("choices") if isinstance(body, dict) else None
        if not isinstance(choices, list) or not choices:
            raise ProviderError("OpenAI-compatible provider returned no choices.")
        message = choices[0].get("message", {}).get("content")
        if not isinstance(message, str) or not message.strip():
            raise ProviderError("OpenAI-compatible provider returned an empty response.")
        return message.strip()


class ProviderManager:
    """Resolve model providers for online, local, or offline execution."""

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    def create(self) -> Any:
        provider_name = (self.settings.provider or "offline").lower()
        if provider_name in {"offline", "none", "local-only"}:
            return OfflineProvider()
        if provider_name in {"ollama", "local"}:
            return OllamaProvider(model=self.settings.model, api_base=self.settings.api_base, api_key=self.settings.api_key)
        if provider_name in {"openai", "openai-compatible", "remote"}:
            return OpenAICompatibleProvider(model=self.settings.model, api_base=self.settings.api_base, api_key=self.settings.api_key)
        raise ProviderError(f"Unsupported provider '{provider_name}'. Use offline, local, or openai.")
