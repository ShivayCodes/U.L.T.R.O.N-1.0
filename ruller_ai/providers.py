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

from .security import validate_model_name, validate_model_output


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
        try:
            self.model = validate_model_name(model)
        except ValueError as exc:
            raise ProviderError("Invalid model name.") from exc
        self.timeout = max(1, min(int(timeout), 180))

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=20, check=False
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
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
        except OSError as exc:
            raise ProviderError("Ollama could not be started.") from exc
        if result.returncode != 0:
            raise ProviderError("Ollama request failed. Check that the selected model is available.")
        try:
            return validate_model_output(result.stdout or "")
        except ValueError as exc:
            raise ProviderError(str(exc)) from exc


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
        _ = parsed.port  # Validate malformed/out-of-range ports.
    except (TypeError, ValueError) as exc:
        raise ProviderError("Invalid model API URL.") from exc
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ProviderError("Model API URL must be an absolute HTTP(S) URL with a hostname.")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ProviderError("Model API URL must not include user information, query parameters, or fragments.")
    if parsed.scheme != "https" and not _is_loopback(parsed.hostname):
        raise ProviderError("Insecure HTTP is allowed only for localhost/loopback model endpoints; use HTTPS for remote APIs.")
    return parsed


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward prompts or Authorization headers to redirected destinations."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenAICompatibleProvider:
    """Generic OpenAI-compatible provider. Remote API keys are HTTPS-only."""

    name = "openai-compatible"
    MAX_RESPONSE_BYTES = 4 * 1024 * 1024

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        *,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout: int = 60,
    ) -> None:
        try:
            self.model = validate_model_name(model)
        except ValueError as exc:
            raise ProviderError("Invalid model name.") from exc
        self.api_base = (api_base or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")).strip()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout = max(1, min(int(timeout), 180))
        self._parsed_base = validate_api_base(self.api_base)
        if self._parsed_base.scheme != "https" and self.api_key:
            raise ProviderError("API keys require HTTPS model endpoints; loopback HTTP is allowed only without an API key.")
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _endpoint(self) -> str:
        return f"{self.api_base.rstrip('/')}/chat/completions"

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ProviderError("A non-empty text prompt is required.")
        if len(prompt) > 8_000:
            raise ProviderError("Prompt exceeds the 8,000-character safety limit.")
        if not self.api_key and self._parsed_base.scheme == "https":
            raise ProviderError("OPENAI_API_KEY is not configured for the selected provider.")
        try:
            token_limit = int(max_tokens)
        except (TypeError, ValueError) as exc:
            raise ProviderError("Invalid model token limit.") from exc
        if token_limit < 1:
            raise ProviderError("Model token limit must be positive.")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [],
            "max_tokens": min(token_limit, 4096),
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
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
            if len(raw) > self.MAX_RESPONSE_BYTES:
                raise ProviderError("Model response exceeded the 4 MiB safety limit.")
            body = json.loads(raw.decode("utf-8"))
        except ProviderError:
            raise
        except urllib.error.HTTPError as exc:
            if 300 <= exc.code < 400:
                raise ProviderError("Model endpoint redirects are blocked for credential and prompt safety.") from exc
            raise ProviderError(f"Model service rejected the request (HTTP {exc.code}). Check model and credentials.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError("Model endpoint is unavailable or the request timed out.") from exc
        except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
            raise ProviderError("Model service returned an invalid response.") from exc

        if not isinstance(body, dict):
            raise ProviderError("Model service returned an invalid response object.")
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderError("Model service returned an invalid completion format.")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ProviderError("Model service returned an invalid completion format.")
        try:
            return validate_model_output(message.get("content"))
        except ValueError as exc:
            raise ProviderError(str(exc)) from exc


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
