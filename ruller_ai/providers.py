"""Model provider interfaces with safe transport and concise failures."""
from __future__ import annotations

import ipaddress
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Safe-to-display provider failure; never contains prompt or credential data."""


class ModelProvider(Protocol):
    name: str

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        """Return model output for a prompt."""


class OfflineProvider:
    name = "offline"

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        raise ProviderError("No model provider is configured.")


class OllamaProvider:
    """Calls a local Ollama server using an argument-list subprocess invocation."""

    name = "ollama"

    def __init__(self, model: str = "llama3.1", *, timeout: int = 60) -> None:
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=20, check=False
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        del max_tokens  # Ollama CLI does not expose a portable per-call token limit.
        if not self.is_available():
            raise ProviderError("Ollama is not installed or not reachable.")
        payload = prompt if system_prompt is None else f"{system_prompt}\n\n{prompt}"
        try:
            result = subprocess.run(
                ["ollama", "run", self.model], input=payload, text=True,
                capture_output=True, timeout=self.timeout, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError("Ollama request timed out.") from exc
        if result.returncode != 0:
            # Never include subprocess stderr/stdout: it may contain submitted content.
            raise ProviderError("Ollama request failed. Check that the selected model is available.")
        response = (result.stdout or "").strip()
        if not response:
            raise ProviderError("Ollama returned an empty response.")
        return response


def _is_loopback(hostname: str) -> bool:
    host = hostname.rstrip(".").casefold()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_api_base(api_base: str) -> urllib.parse.ParseResult:
    """Validate API URL and prevent credentials or prompts going to remote HTTP."""
    try:
        parsed = urllib.parse.urlparse(api_base)
        # Accessing .port also validates malformed/out-of-range ports.
        _ = parsed.port
    except (TypeError, ValueError) as exc:
        raise ProviderError("Invalid model API URL.") from exc
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ProviderError("Model API URL must be an absolute HTTP(S) URL with a hostname.")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ProviderError("Model API URL must not include user information, query parameters, or fragments.")
    if parsed.scheme != "https" and not _is_loopback(parsed.hostname):
        raise ProviderError("Insecure HTTP is allowed only for localhost/loopback model endpoints; use HTTPS for remote APIs.")
    return parsed


class OpenAICompatibleProvider:
    """Generic OpenAI-compatible provider. Remote API keys are HTTPS-only."""

    name = "openai-compatible"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        *,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.model = model
        self.api_base = (api_base or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")).strip()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout = timeout
        self._parsed_base = validate_api_base(self.api_base)

    def _endpoint(self) -> str:
        return f"{self.api_base.rstrip('/')}/chat/completions"

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        if not self.api_key and self._parsed_base.scheme == "https":
            raise ProviderError("OPENAI_API_KEY is not configured for the selected provider.")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [],
            "max_tokens": max(1, min(int(max_tokens), 4096)),
        }
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        request = urllib.request.Request(
            self._endpoint(), data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST",
        )
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise ProviderError("Model response exceeded the 4 MiB safety limit.")
            body = json.loads(raw.decode("utf-8"))
        except ProviderError:
            raise
        except urllib.error.HTTPError as exc:
            # Response bodies can echo request data; deliberately do not display/log them.
            raise ProviderError(f"Model service rejected the request (HTTP {exc.code}). Check model and credentials.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError("Model endpoint is unavailable or the request timed out.") from exc
        except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
            raise ProviderError("Model service returned an invalid response.") from exc
        try:
            choices = body.get("choices") or []
            content = choices[0].get("message", {}).get("content") or ""
        except (AttributeError, IndexError, TypeError) as exc:
            raise ProviderError("Model service returned an invalid completion format.") from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("Model returned an empty completion.")
        return content.strip()


def build_provider(
    provider_name: str | None,
    *,
    model: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
) -> ModelProvider | None:
    """Build configured provider, or return None for offline-only mode."""
    name = (provider_name or "offline").strip().casefold()
    if name in {"", "offline", "none"}:
        return None
    if name in {"ollama", "local-ollama", "local_ollama"}:
        return OllamaProvider(model or "llama3.1")
    if name in {"openai", "openai-compatible", "openai_compatible", "openai-compatible-http"}:
        return OpenAICompatibleProvider(model or "gpt-4o-mini", api_base=api_base, api_key=api_key)
    raise ProviderError("Unknown model provider. Choose offline, ollama, or openai.")
