# ULTRON security notes

The memory sidecar SHA-256 digest detects accidental or one-sided edits. It is not authenticated tamper protection against an account/process that can modify both files.

Remote OpenAI-compatible endpoints require HTTPS. Credentialed HTTP is rejected, even on loopback; loopback HTTP is supported only without an API key. API URLs reject userinfo, query strings, fragments, controls, invalid schemes/hosts, and redirects are not followed. Provider prompts and model identifiers are bounded and validated; responses are size-limited. Provider errors are sanitized and must not include prompts, headers, keys, or response bodies.

The GUI gates hosted model use behind an explicit session consent control. Offline mode does not contact a model provider. User input is length-checked and control characters are rejected before it is displayed/sent. API keys are held only in process memory and must not be put on command lines. Health checks don't send chat prompts; hosted checks use the provider's `/models` endpoint and may not be supported by all compatible services.

Adaptive examples and feedback are local reference data, not model training. When hosted mode is consented, relevant examples/notes can be included in the prompt and therefore sent to the configured provider. Review data before teaching it and do not include secrets.

These controls address specific failure paths but cannot guarantee that all incidents, exploitation, or leaks are prevented. Secure the OS account, review provider retention policies, update dependencies, and test the application on supported Windows versions.
