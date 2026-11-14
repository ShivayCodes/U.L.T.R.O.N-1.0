# OmniAgent Studio

## Product requirements

See the full requirements in `docs/PRD.md` and the repository root `PRD.md`.

## What this project includes

- Local-first orchestration with opt-in model providers
- SQLite-backed session persistence
- Multi-provider support for offline/local/remote APIs
- Skill registry for coding, summarization, and media generation workflows
- CLI status and chat commands
- Secure-by-default defaults aligned with the PRD

## Quick start

```bash
python -m pip install -e .
omniagent --status
omniagent --chat "Plan a simple workflow for my AI project"
```

## Architecture emphasis

The project intentionally follows the PRD's core design:

- privacy-first local defaults
- modular skill execution
- provider abstraction for local and hosted models
- session storage and workflow planning
- extensible plugin architecture
