# OmniAgent Studio

## Product Requirements Document (PRD)

This repository now implements an MVP aligned with the PRD for a local-first AI orchestration platform.

### Core goals

- Unified orchestration for coding assistance, automation, and specialized skills
- Local-first privacy and secure defaults
- Multi-provider model support with explicit opt-in cloud access
- SQLite-backed session persistence
- Modular skills engine and planner-based routing

### Scope in this repository

- CLI entrypoints for local-first AI interaction
- local storage and session tracking
- provider abstraction for offline, Ollama, and OpenAI-compatible APIs
- plugin registry for reusable tasks and workflows
- docs and project configuration aligned to the PRD

### Suggested next milestones

1. Add a desktop/web dashboard frontend
2. Expand plugin marketplace support
3. Add deeper codebase-aware tool execution and security prompts
4. Add TDD and task execution flow for engineering work
5. Add real media / workflow automation skill adapters
