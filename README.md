# U.L.T.R.O.N 1.0

**Beyond Conventional AI. Toward Adaptive Intelligence.**

U.L.T.R.O.N 1.0 is an **offline-first Python assistant prototype** with local conversation memory, a small knowledge base, explainable text retrieval, and a constrained arithmetic tool. It is designed as a transparent, testable foundation for adaptive intelligence research.

> **Important:** The current version is not a trained language model. It uses explicit commands, lexical retrieval, and deterministic rules. It does not claim AGI, consciousness, or unlimited reasoning.

## Features

- **Python-first and lightweight:** Python 3.10+; no third-party runtime dependencies.
- **Local memory:** stores bounded conversation history in JSON on your machine.
- **Knowledge ingestion:** learn text directly or import supported local text files.
- **Explainable retrieval:** shows matching passages and their source.
- **Safe calculator:** parses arithmetic through an AST allowlist; never uses `eval()` or `exec()`.
- **CLI interface:** interactive terminal assistant with help, stats, search, and memory controls.
- **Tests and CI:** unit tests, bytecode compilation, and supported Python-version matrix.

## Quick start

Install Python 3.10 or newer, then from the repository root:

```powershell
# Optional: create an isolated environment on Windows
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Run directly; there are no required third-party packages
python -m ruller_ai
```

Run the CLI as a package rather than executing `ruller_ai\cli.py` directly;
direct execution does not provide the package context required by its relative
imports.

If PowerShell blocks activation, you can skip activation and run `.venv\Scripts\python.exe -m ruller_ai`.

On macOS/Linux, activate with `source .venv/bin/activate`.

## Try it

```text
You> /help
You> /calc 12 * (3 + 2)
You> /learn Python is useful for automation and data analysis.
You> /search Python automation
You> /ingest path/to/notes.txt
You> /stats
You> /exit
```

Supported commands:

| Command | Purpose |
|---|---|
| `/help` | Show commands and notes |
| `/calc EXPRESSION` | Safely calculate basic arithmetic |
| `/learn TEXT` | Add a passage to the local knowledge base |
| `/search QUERY` | Search stored passages |
| `/ingest PATH` | Import a supported text file up to 1 MB |
| `/remember NOTE` | Store a note in local conversation memory |
| `/stats` | Show memory and knowledge counts |
| `/time` | Show local system time |
| `/clear` | Clear conversation memory |
| `/exit` | Quit the CLI |

## Choose where data is stored

By default, U.L.T.R.O.N 1.0 stores files under `~/.ruller_ai/`. To use a custom location:

```powershell
python -m ruller_ai --data-dir .\ruller-data
```

Treat memory and knowledge files as personal data. Do not ingest secrets or files you do not have permission to use.

## Run tests

No pytest installation is required; tests use Python's standard library:

```powershell
python -m compileall -q ruller_ai tests
python -m unittest discover -s tests -v
```

GitHub Actions runs these checks on Python 3.10–3.13. A passing workflow is evidence for the tested paths, not a guarantee that software has zero bugs.

## Project layout

```text
ruller_ai/
  __init__.py
  __main__.py
  cli.py
  config.py
  engine.py
  knowledge.py
  memory.py
  reasoning.py
  storage.py
  vision.py
  providers.py
tests/
  test_core.py
docs/
  ARCHITECTURE.md
.github/workflows/ci.yml
pyproject.toml
```

See [Architecture and limitations](docs/ARCHITECTURE.md) for design details and planned extension points.

## Roadmap

1. Add a typed model-provider interface with optional local-model integration.
2. Add retrieval evaluation and improved chunking.
3. Add explicit feedback records and measurable evaluation benchmarks.
4. Add permissioned tools, audit logs, and stronger data-management controls.
5. Add an optional UI only after the core behavior is tested.

These roadmap items are **not implemented yet**. The project prioritizes transparent behavior, safe defaults, and a testable foundation over claims of unrestricted intelligence.
