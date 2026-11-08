"""Model provider interfaces with validated configuration and safe transport."""
from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Safe-to-display provider failure; excludes prompts and credentials."""


class ModelProvider(Protocol):
    name: str

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Do not follow endpoint redirects with request bodies or authorization headers."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _open_no_redirect(request: urllib.request.Request, timeout: int) -> Any:
    return urllib.request.build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


class OfflineProvider:
    name = "offline"

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        raise ProviderError("No model provider is configured.")


class OllamaProvider:
    """Calls local Ollama using safe argument-list subprocess invocations."""

    name = "ollama"
    MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")

    def __init__(self, model: str = "llama3.1", *, timeout: int = 60) -> None:
        self.model = _validate_model(model, self.MODEL_RE)
        self.timeout = max(1, min(int(timeout), 300))

    def health_check(self) -> tuple[bool, str]:
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=8, check=False)
        except FileNotFoundError:
            return False, "Ollama executable not found; install/start Ollama."
        except subprocess.TimeoutExpired:
            return False, "Ollama did not respond within 8 seconds."
        if result.returncode != 0:
            return False, "Ollama is not available. Start the local Ollama service."
        installed = {line.split()[0] for line in (result.stdout or "").splitlines()[1:] if line.split()}
        if self.model not in installed:
            return False, f"Ollama is running, but model '{self.model}' is not listed as installed."
        return True, f"Ollama is running and model '{self.model}' is installed."

    def is_available(self) -> bool:
        return self.health_check()[0]

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        del max_tokens  # Ollama CLI has no portable per-call token-limit option.
        _validate_prompt(prompt, system_prompt)
        ok, detail = self.health_check()
        if not ok:
            raise ProviderError(detail)
        payload = prompt if system_prompt is None else f"{system_prompt}\n\n{prompt}"
        try:
            result = subprocess.run(["ollama", "run", self.model], input=payload, text=True,
                                    capture_output=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ProviderError("Ollama request timed out.") from exc
        if result.returncode != 0:
            raise ProviderError("Ollama request failed. Check that the selected model is available.")
        response = (result.stdout or "").strip()
        if not response:
            raise ProviderError("Ollama returned an empty response.")
        return response[:MAX_RESPONSE_CHARS]


def _validate_model(model: str, pattern: re.Pattern[str]) -> str:
    value = str(model).strip()
    if not value or len(value) > 200 or not pattern.fullmatch(value) or ".." in value:
        raise ProviderError("Invalid model identifier. Use a short name containing letters, digits, dot, underscore, colon, slash, or hyphen.")
    return value


MAX_PROMPT_CHARS = 16_000
MAX_SYSTEM_PROMPT_CHARS = 4_000
MAX_RESPONSE_CHARS = 64_000


def _validate_prompt(prompt: str, system_prompt: str | None) -> None:
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
        raise ProviderError(f"Prompt must be non-empty and no longer than {MAX_PROMPT_CHARS} characters.")
    if system_prompt is not None and (not isinstance(system_prompt, str) or len(system_prompt) > MAX_SYSTEM_PROMPT_CHARS):
        raise ProviderError(f"System prompt must be no longer than {MAX_SYSTEM_PROMPT_CHARS} characters.")


def _is_loopback(hostname: str) -> bool:
    host = hostname.rstrip(".").casefold()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_api_base(api_base: str) -> urllib.parse.ParseResult:
    if not isinstance(api_base, str) or not api_base or len(api_base) > 2048 or any(ord(char) < 32 or ord(char) == 127 for char in api_base):
        raise ProviderError("Invalid model API URL.")
    try:
        parsed = urllib.parse.urlparse(api_base)
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
    """OpenAI-compatible provider with bounded requests and no credentialed redirects."""

    name = "openai-compatible"
    MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")

    def __init__(self, model: str = "gpt-4o-mini", *, api_base: str | None = None,
                 api_key: str | None = None, timeout: int = 60) -> None:
        self.model = _validate_model(model, self.MODEL_RE)
        self.api_base = (api_base or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")).strip()
        self._parsed_base = validate_api_base(self.api_base)
        self.api_key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip() or None
        if self.api_key and (len(self.api_key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in self.api_key)):
            raise ProviderError("Invalid API key format.")
        if self.api_key and self._parsed_base.scheme != "https":
            raise ProviderError("API keys may only be sent over HTTPS. Remove the key for a local HTTP endpoint.")
        self.timeout = max(1, min(int(timeout), 300))

    def _endpoint(self) -> str:
        return f"{self.api_base.rstrip('/')}/chat/completions"

    def health_check(self) -> tuple[bool, str]:
        if self._parsed_base.scheme == "https" and not self.api_key:
            return False, "API key is missing. Add one in the sidebar or set OPENAI_API_KEY."
        endpoint = f"{self.api_base.rstrip('/')}/models"
        request = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with _open_no_redirect(request, min(self.timeout, 8)) as response:
                if not 200 <= response.status < 300:
                    return False, f"API returned HTTP {response.status}."
                if len(response.read(1_048_577)) > 1_048_576:
                    return False, "Health response exceeded the 1 MiB limit."
            return True, "API endpoint responded successfully."
        except urllib.error.HTTPError as exc:
            return False, f"API health check returned HTTP {exc.code}; verify key and endpoint (redirects are not followed)."
        except (urllib.error.URLError, TimeoutError, OSError):
            return False, "API endpoint is unreachable or timed out. Verify URL and network."

    def generate(self, prompt: str, *, system_prompt: str | None = None, max_tokens: int = 512) -> str:
        _validate_prompt(prompt, system_prompt)
        if not self.api_key and self._parsed_base.scheme == "https":
            raise ProviderError("OPENAI_API_KEY is not configured for the selected provider.")
        payload: dict[str, Any] = {"model": self.model, "messages": [], "max_tokens": max(1, min(int(max_tokens), 4096))}
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})
        payload["messages"].append({"role": "user", "content": prompt})
        request = urllib.request.Request(self._endpoint(), data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        if self.api_key:
            request.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with _open_no_redirect(request, self.timeout) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise ProviderError("Model response exceeded the 4 MiB safety limit.")
            body = json.loads(raw.decode("utf-8"))
        except ProviderError:
            raise
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"Model service returned HTTP {exc.code}; redirects are not followed. Check model and credentials.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderError("Model endpoint is unavailable or the request timed out.") from exc
        except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
            raise ProviderError("Model service returned an invalid response.") from exc
        try:
            content = (body.get("choices") or [])[0].get("message", {}).get("content") or ""
        except (AttributeError, IndexError, TypeError) as exc:
            raise ProviderError("Model service returned an invalid completion format.") from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("Model returned an empty completion.")
        return content.strip()[:MAX_RESPONSE_CHARS]


def build_provider(provider_name: str | None, *, model: str | None = None,
                   api_base: str | None = None, api_key: str | None = None) -> ModelProvider | None:
    name = (provider_name or "offline").strip().casefold()
    if name in {"", "offline", "none"}:
        return None
    if name in {"ollama", "local-ollama", "local_ollama"}:
        return OllamaProvider(model or "llama3.1")
    if name in {"openai", "openai-compatible", "openai_compatible", "openai-compatible-http"}:
        return OpenAICompatibleProvider(model or "gpt-4o-mini", api_base=api_base, api_key=api_key)
    raise ProviderError("Unknown model provider. Choose offline, ollama, or openai.")
