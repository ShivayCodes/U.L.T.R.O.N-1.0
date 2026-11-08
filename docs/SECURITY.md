# ULTRON security notes

## Security boundaries

ULTRON is an offline-first desktop assistant. The language model is used only to generate text; model output is not interpreted as a command and is not wired to arbitrary shell, Python, filesystem, or tool execution. Built-in tools are separately allowlisted and permission checked by application code. Keep that separation: never dispatch a tool solely because a model suggested it.

System instructions tell the model to treat imported files, retrieved memory, web pages, quoted text, and tool output as untrusted data. This is a useful prompt-injection mitigation, **not a reliable prompt-injection detector or security boundary**. A model can still be manipulated. Do not give the model capabilities that would make an instruction-following failure destructive; enforce authorization in application code.

## Provider configuration and transport

- Remote OpenAI-compatible endpoints must use HTTPS. Plain HTTP is accepted only for loopback hosts to support local model servers.
- API URLs containing user information, query strings, or fragments are rejected.
- Redirects are blocked so prompts and bearer credentials cannot be forwarded to a different endpoint.
- Provider and model identifiers, timeouts, token limits, response types, and response sizes are validated.
- Never place API keys in command-line arguments or source files. Prefer environment variables or the hidden CLI prompt. GUI keys remain in process memory only.
- A custom HTTPS endpoint is still a trust decision: verify that you control or trust the endpoint before sending prompts.

## Input and data handling

- Chat input is bounded by the configured character limit and rejects unsupported control characters.
- Obvious credential assignments and bearer tokens are redacted before conversation memory and knowledge persistence.
- If a chat prompt matches the sensitive-value patterns, remote model transmission is blocked and ULTRON uses its local fallback.
- GUI input enforces the same configured character limit and suppresses raw exception details.
- Logs and user-facing provider errors must not include prompts, authorization headers, response bodies, or raw exception text.

Redaction is best-effort. It does not identify every possible secret format, and it does not encrypt local data. Treat the Windows account and data directory as sensitive; use OS account protections and disk encryption where appropriate. Previously saved history is not automatically scrubbed by this update.

## Memory integrity

The adjacent SHA-256 sidecar detects accidental or one-sided edits. It is not authenticated tamper protection: someone with write access to the same account can edit both the memory file and digest. Do not rely on it against a malicious local user or process.

## Operational guidance

- Keep Python and dependencies updated.
- Do not paste passwords, access tokens, private keys, or confidential data into chat.
- Review a provider's retention and training policy before using a hosted endpoint.
- Treat imported documents and web content as untrusted; verify facts and sources.
- Run the full test suite on Windows before treating a release as production-ready.

These controls reduce specific risks; they cannot guarantee that all exploitation, prompt injection, or data leakage is impossible.
