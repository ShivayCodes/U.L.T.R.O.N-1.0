# Product Requirements Document (PRD)
## U.L.T.R.O.N 1.0 — Small, Offline-First AI Assistant

- **Document status:** Proposed product specification
- **Version:** 1.0
- **Last updated:** 2026-11-02
- **Product type:** Lightweight, modular Python assistant
- **Primary interface:** Command-line interface (CLI)
- **Target runtime:** Python 3.10+
- **Default operating mode:** Local/offline; network access is optional and explicit

---

## 1. Executive summary

U.L.T.R.O.N 1.0 is a small, transparent personal AI-assistant foundation. It should help an individual capture notes, search a private knowledge collection, ask questions over stored material, perform narrowly scoped calculations, and optionally use a language model through a clearly controlled provider interface.

The product must remain useful on modest consumer hardware. It should prioritize predictable behavior, privacy, low resource consumption, explainability, and maintainability over model size or claims of general intelligence.

**Product truth:** the existing implementation is a rule-based assistant with lexical retrieval and a constrained arithmetic evaluator. It is not currently a trained language model. Model-based generation, semantic embeddings, autonomous planning, and self-improvement are future capabilities and must not be represented as implemented until delivered and evaluated.

## 2. Problem statement

A user needs a private assistant that can organize a small body of personal learning material and retrieve useful information without requiring a cloud account or a high-end computer. Large hosted systems can introduce recurring costs, network dependency, data-sharing concerns, and unnecessary complexity. A small local application can address the basic workflow if its limitations are explicit and its data handling is safe.

## 3. Product vision and principles

### Vision

Deliver a dependable local assistant that grows through small, measurable, independently testable capabilities.

### Principles

1. **Offline-first:** core memory, notes, retrieval, calculations, and CLI use work without internet access.
2. **Privacy by default:** user data remains local unless the user explicitly enables a network provider or export.
3. **Small footprint:** avoid mandatory heavyweight frameworks and models.
4. **Honest capability boundaries:** distinguish deterministic functions, retrieved evidence, and model-generated output.
5. **Explainability:** show relevant source passages and disclose when no reliable answer is available.
6. **Least privilege:** tools and file access are narrow, permissioned, and auditable.
7. **Incremental delivery:** each milestone has acceptance criteria and measurable quality gates.

## 4. Goals and non-goals

### Goals

- Provide a stable CLI assistant for individual users.
- Store conversation memory, notes, and knowledge locally.
- Ingest supported text documents within configurable size limits.
- Retrieve relevant passages and identify their source.
- Support safe arithmetic without dynamic code execution.
- Offer an optional, replaceable model-provider interface without making it mandatory.
- Run on modest Windows, Linux, and macOS systems.
- Provide tests, documentation, data export, and clear recovery behavior.

### Non-goals for version 1.x

- AGI, consciousness, emotions, or unrestricted reasoning.
- Training a foundation model from scratch.
- Autonomous modification of source code, system settings, or user files.
- Unrestricted shell, browser, or operating-system control.
- Multi-user hosting, public API service, or enterprise identity management.
- Guaranteed factual correctness or professional medical, legal, or financial advice.
- Real-time voice, video understanding, or advanced image generation.
- Background surveillance or collection of user activity.

## 5. Target users and primary use cases

### Primary user

A technically curious individual, student, or developer who wants a private learning and productivity assistant on a personal computer.

### Core user journeys

1. **Ask and retrieve:** enter a question; the assistant searches local knowledge and returns relevant passages with source references.
2. **Capture knowledge:** add a note or ingest an allowed text file; the item is stored locally and becomes searchable.
3. **Recall context:** review or search recent conversation history and saved notes.
4. **Calculate:** run a supported arithmetic expression through the safe calculator.
5. **Inspect and control data:** view storage statistics, clear conversation history, export data, and choose a data directory.
6. **Optional model response:** explicitly configure a local or remote model provider; see when a provider is being used and handle failures safely.

## 6. Scope and release priorities

| Priority | Capability | Release expectation |
|---|---|---|
| P0 | CLI, help, exit, configuration, local data directory | Required |
| P0 | Local notes and bounded conversation memory | Required |
| P0 | Text ingestion with file/type/size validation | Required |
| P0 | Explainable lexical retrieval with source attribution | Required |
| P0 | Safe arithmetic evaluator | Required |
| P0 | Input validation, safe storage, error handling, tests | Required |
| P1 | Export, backup, restore, and data deletion controls | Target for 1.x |
| P1 | Typed model-provider abstraction and explicit network consent | Target for 1.x |
| P1 | Retrieval evaluation dataset and benchmark command | Target for 1.x |
| P2 | Optional embeddings and semantic retrieval | Later, opt-in dependency |
| P2 | Optional lightweight local language model | Hardware-dependent experiment |
| P2 | Optional OCR improvements and image metadata handling | Later |
| P2 | Desktop UI | Only after CLI workflows are stable |

P0 features define the minimum reliable product. P1 and P2 features must not be treated as delivered until implementation and tests exist.

## 7. Functional requirements

### FR-01 — CLI and command routing

- The application shall provide an interactive CLI and a documented command set.
- Unknown commands shall return a helpful error without terminating the application.
- Commands shall validate argument count, type, and length before processing.
- The CLI shall support a non-interactive invocation path where practical for automation.
- Help output shall accurately reflect implemented commands.

**Acceptance:** all documented commands have tests for valid input, invalid input, and expected failure behavior.

### FR-02 — Local memory

- Conversation history shall be stored in the selected local data directory.
- Memory retention shall have configurable record and per-record size limits.
- The application shall expose commands to inspect, search, clear, and export memory.
- Clear operations shall leave the intended data empty; command confirmations must not silently repopulate cleared history.
- The user shall be told where data is stored.

**Acceptance:** tests verify retention bounds, persistence after restart, clear semantics, and malformed-file recovery.

### FR-03 — Knowledge ingestion

- Initial supported formats shall be plain text and Markdown; other formats require explicit support.
- Ingestion shall enforce an allowlist of file extensions and a configurable maximum file size.
- The application shall reject unsupported encodings or handle them with a documented fallback.
- The source path, import time, and stable document identifier shall be retained where appropriate.
- File access shall be constrained to user-selected paths; future UI/server interfaces must enforce an allowed-root policy.
- The application shall not execute imported content.

**Acceptance:** tests cover valid files, empty files, oversized files, unsupported extensions, invalid encodings, path traversal attempts, and unreadable files.

### FR-04 — Retrieval and answer presentation

- Retrieval shall return ranked passages, not silently invent supporting content.
- Results shall include document/source identity and a relevance score or understandable ranking explanation.
- Empty or weak matches shall produce an explicit “no useful local evidence found” response.
- The initial lexical retriever shall remain dependency-free.
- Any future semantic retriever shall be optional and comparable against the lexical baseline.

**Acceptance:** a fixed evaluation set measures recall@k, precision@k, and ranking quality; regressions are tracked across releases.

### FR-05 — Safe arithmetic

- The calculator shall parse expressions using a strict AST allowlist.
- Only documented numeric constants and arithmetic operators shall be accepted.
- Calls, attribute access, imports, names, comprehensions, and arbitrary expressions shall be rejected.
- Numeric magnitude, exponentiation, and expression complexity shall be bounded to reduce denial-of-service risk.

**Acceptance:** positive arithmetic tests and adversarial parser tests demonstrate that arbitrary code is never executed.

### FR-06 — Optional model provider

- Model integration shall be behind a typed provider interface.
- The core application shall work when no provider is configured.
- Provider selection, endpoint, model identifier, and network status shall be visible in configuration and diagnostics.
- Remote requests shall require explicit user configuration and consent.
- HTTPS shall be required by default for remote endpoints; insecure HTTP shall require a deliberate opt-in and should be limited to loopback for local development.
- Requests shall have connection/read timeouts, bounded input/output sizes, and clear error handling.
- Secrets shall be read from environment variables or an appropriate local secret store, never committed to source control or printed in logs.
- Provider output shall be treated as untrusted data and shall not directly trigger tools or shell commands.

**Acceptance:** tests cover missing credentials, invalid configuration, timeout, HTTP policy, oversized responses, provider errors, and offline operation.

### FR-07 — Tool execution and permissions

- Version 1.x shall expose only built-in, narrowly scoped tools.
- No arbitrary shell or Python execution shall be available to model output.
- Every future tool shall declare its name, purpose, input schema, permission requirement, and side effects.
- Destructive or external actions shall require direct user confirmation.
- Tool invocations shall be logged without storing secrets.

**Acceptance:** unapproved tool calls are rejected and tests prove that model text cannot bypass permission checks.

### FR-08 — Storage, backup, and recovery

- Writes shall be atomic and safe against predictable temporary-file races.
- Temporary files shall be uniquely and securely created in the destination directory and cleaned up on failure.
- Loaded JSON shall have byte, record-count, and field-length limits plus per-record schema validation.
- Corrupt data shall produce a clear warning and a recoverable backup path where possible.
- The user shall be able to export and restore their own data using a documented format.
- File permissions should be restrictive where the platform supports them.

**Acceptance:** tests cover interrupted writes, malformed JSON, oversized files, invalid records, and backup/restore round trips.

### FR-09 — OCR and image inputs (optional feature)

- OCR shall be an optional capability and shall not be required for core operation.
- Supported image formats, maximum file size, dimensions, and pixel count shall be documented and enforced.
- OCR execution shall have a timeout and bounded output.
- Decompression-bomb and malformed-image errors shall be handled safely.
- OCR results shall be labeled as extracted text and not treated as verified facts.

**Acceptance:** tests cover unsupported images, oversized dimensions, OCR timeout, malformed files, and missing OCR dependency.

### FR-10 — Observability and diagnostics

- The application shall provide a diagnostic command showing version, Python version, data directory, enabled capabilities, and storage counts.
- Logs shall be structured or consistently formatted, bounded, and free of credentials and private note contents by default.
- Errors shall include actionable guidance without exposing stack traces to normal CLI users; debug mode may show diagnostic details.
- Metrics shall not require telemetry or network transmission.

**Acceptance:** diagnostics work offline and tests ensure secret values are redacted.

## 8. Non-functional requirements

| Area | Requirement / initial target |
|---|---|
| Platform | Python 3.10+; Windows 11, current Linux distributions, and macOS |
| Dependencies | Zero mandatory third-party runtime dependencies for core features |
| Memory | Target under 150 MB RSS for core CLI + small knowledge corpus; measure on reference hardware |
| Startup | Target under 2 seconds on reference hardware, excluding optional model startup |
| Retrieval latency | Target under 500 ms for 10,000 short passages on reference hardware |
| Ingestion | Enforce configurable per-file and total-corpus limits |
| Reliability | No uncaught exception for expected user/input/storage/provider failures |
| Privacy | Local-only by default; no telemetry by default |
| Security | Input validation, least privilege, bounded resources, safe serialization, secret redaction |
| Maintainability | Typed interfaces where useful, modular components, documented public behavior |
| Accessibility | CLI prompts and errors readable, consistent, and usable with keyboard-only interaction |
| Portability | Avoid platform-specific behavior unless isolated behind an adapter |

These are engineering targets, not measured claims. Establish a documented reference machine and benchmark before treating targets as release gates.

## 9. High-level architecture

Recommended component boundaries:

1. **CLI / presentation layer:** parses user commands and renders responses.
2. **Application engine:** coordinates use cases; contains no direct network or filesystem policy.
3. **Domain layer:** message, note, document, retrieval result, and tool request data structures.
4. **Memory repository:** validates and persists conversation records.
5. **Knowledge repository:** ingestion, chunking, metadata, and retrieval.
6. **Reasoning / calculator:** deterministic rules and safe arithmetic.
7. **Provider adapter:** optional local or remote model transport.
8. **Tool registry:** explicit allowlisted tools with permission checks.
9. **Storage/security utilities:** atomic writes, path validation, size limits, redaction.
10. **Evaluation and test harness:** repeatable quality, safety, and performance checks.

Keep provider-specific code and optional heavy dependencies outside the core import path. Define interfaces before adding additional backends.

## 10. Data model and lifecycle

Minimum conceptual records:

- **ConversationMessage:** identifier, role, content, timestamp, optional metadata.
- **Note:** identifier, content, created/updated timestamps, tags.
- **Document:** identifier, source name/path metadata, content hash, import timestamp, format, status.
- **Chunk:** identifier, document identifier, text, ordinal, optional metadata.
- **RetrievalResult:** chunk/document reference, score, ranking explanation.
- **AuditEvent:** timestamp, action, outcome, permission decision; never include secrets.

Lifecycle requirements:

- Data is created only from user commands or explicitly enabled integrations.
- Imported files are copied or parsed according to documented behavior; original files are not modified.
- Deletion behavior must specify whether it removes a note, a document, its chunks, or conversation history.
- Export shall use a documented, versioned format.
- Schema changes shall include migration or safe reset guidance.

## 11. Security, privacy, and abuse-case requirements

Threats to address include malicious or oversized imported files, malformed local data, path traversal, symlink races in writable directories, untrusted model/provider output, prompt injection inside retrieved documents, network credential exposure, resource exhaustion, and accidental disclosure through logs.

Required controls:

- Validate all external inputs and persisted records.
- Apply file, record, token, image-dimension, timeout, and output limits.
- Resolve and validate paths against explicit user permissions.
- Treat retrieved documents and model responses as untrusted content.
- Never allow retrieved instructions to override system or tool permission policy.
- Use HTTPS by default for remote provider calls.
- Keep secrets out of repository files, exceptions, and logs.
- Add security regression tests for every reported vulnerability.
- Provide a responsible vulnerability-reporting path in the repository.

A security review is required before enabling a network-facing server, multi-user mode, or autonomous tool execution.

## 12. Quality strategy and acceptance gates

Every release candidate must pass:

1. Unit tests for command parsing, memory, ingestion, retrieval, calculator, storage, and provider adapters.
2. Adversarial tests for path traversal, malformed files, oversized input, parser abuse, prompt injection, and secret redaction.
3. Integration tests for end-to-end CLI workflows and restart persistence.
4. Offline test proving core functionality works without network access.
5. Performance benchmark on a documented reference machine.
6. Dependency and secret scanning in CI where supported.
7. Documentation check: installation, configuration, data location, privacy, limitations, backup, and troubleshooting.

No release may claim a feature is complete solely because its interface exists; implementation, tests, documentation, and acceptance evidence are required.

## 13. Success metrics

Measure locally and report aggregate benchmark results without transmitting user data.

- **Task completion:** percentage of benchmark tasks completed correctly.
- **Retrieval quality:** precision@5, recall@5, and mean reciprocal rank on a labeled test set.
- **Grounding:** percentage of knowledge answers with valid source references.
- **Safety:** pass rate on adversarial input and permission-boundary tests.
- **Reliability:** expected-failure handling rate and uncaught exception count.
- **Performance:** startup time, retrieval latency, peak RSS, and corpus size.
- **Privacy:** zero network requests in default offline mode; zero secrets in logs.
- **Maintainability:** test coverage of critical modules and CI success rate.

Initial target values should be established after a baseline run; do not fabricate benchmark results.

## 14. Delivery plan

### Phase 0 — Stabilize the current baseline
- Fix and test memory clear semantics.
- Harden atomic file writes and JSON loading.
- Add ingestion and OCR resource limits.
- Enforce provider transport security and timeouts.
- Document current limitations and threat model.

**Exit criteria:** critical security regression tests pass; existing CLI behavior remains backward compatible where practical.

### Phase 1 — Reliable personal knowledge assistant
- Formalize note/document schemas.
- Add robust ingestion, chunking, source references, and retrieval evaluation.
- Add export, backup, restore, and deletion workflows.
- Improve diagnostics and error messages.

**Exit criteria:** benchmark corpus and end-to-end acceptance tests pass.

### Phase 2 — Optional model assistance
- Finalize typed provider interface.
- Add one local provider adapter and optionally one remote-compatible adapter.
- Add bounded prompts/responses, explicit network consent, and provider status.
- Evaluate answer quality and groundedness against a no-model baseline.

**Exit criteria:** provider can be disabled without affecting core operation; offline and failure tests pass.

### Phase 3 — Optional semantic retrieval and UI
- Evaluate lightweight embeddings against lexical retrieval.
- Add semantic retrieval only if it produces measurable improvement for acceptable resource cost.
- Consider a desktop UI after CLI and APIs are stable.

**Exit criteria:** documented quality/performance trade-off and no regression to core offline operation.

## 15. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Scope grows into an unrealistic “unlimited AI” project | Delays and unclear acceptance | Keep versioned scope and measurable requirements |
| Small hardware cannot run selected local models | Poor latency or unusable memory pressure | Make model optional; publish hardware profiles and benchmarks |
| Lexical retrieval misses semantic matches | Weak answer relevance | Build labeled evaluation set; compare optional embeddings |
| Model hallucinates or follows injected instructions | Incorrect or unsafe behavior | Source grounding, untrusted-input boundaries, permissioned tools |
| Local files are corrupted or exposed | Data loss or privacy harm | Atomic writes, restrictive permissions, backups, schema validation |
| Provider endpoint leaks credentials | Credential compromise | HTTPS policy, timeouts, secret redaction, local-only default |
| OCR or ingestion exhausts resources | Denial of service | Strict size/dimension/time limits |
| “Self-learning” changes behavior unpredictably | Loss of control and reproducibility | Store feedback as data; require reviewed, versioned updates; no autonomous code modification |

## 16. Open product decisions

These decisions must be made before implementing the related capability:

- Which operating systems and minimum hardware should be official support targets?
- What is the default maximum corpus size and retention period?
- Should local model support use a separately installed runtime or a Python-native backend?
- Which model licenses and distribution constraints are acceptable?
- What export format and migration policy should be guaranteed?
- Should OCR remain an optional extra?
- What exact benchmark dataset represents the intended user's tasks?

Until decided, use conservative defaults and keep these capabilities optional.

## 17. Definition of done

A requirement is done only when:
- the behavior is implemented;
- success and failure paths are tested;
- resource and security limits are enforced;
- documentation describes actual behavior and limitations;
- CI passes on supported Python versions; and
- acceptance evidence is recorded in the pull request.

## 18. Current implementation versus this PRD

This PRD describes the intended product, not a claim that all requirements already exist. The current repository provides a Python CLI, local JSON memory and knowledge storage, lexical retrieval, a constrained arithmetic evaluator, and optional OCR/provider modules. Requirements such as robust backup/restore, comprehensive schema validation, permissioned tools, benchmark harnesses, and hardened provider controls require implementation and verification.

See [the architecture document](ARCHITECTURE.md) and the repository security review issue for current implementation details and tracked hardening work.
