# ULTRON security notes

The memory sidecar SHA-256 digest is a consistency check that can detect accidental or one-sided edits. It is not authenticated tamper protection: someone with write access to the same account can edit both the memory file and digest. Treat local files as private data and use operating-system account protections; do not rely on this check against a malicious local user or process.

Remote OpenAI-compatible API URLs must use HTTPS. Plain HTTP is accepted only for loopback hosts (`localhost`, `127.0.0.1`, and `::1`) to support local model servers. Provider errors shown in the UI/CLI are sanitized and do not include request bodies or authorization credentials. Configure keys through environment variables or the hidden CLI prompt, not command-line arguments.

These controls reduce specific risks identified in the code review, but cannot guarantee that incidents or data leaks are impossible. Keep Python and dependencies updated, protect the Windows account and device, and consider remote-provider data policies before sending prompts.
