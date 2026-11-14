# ULTRON 1.0

**ULTRON is an offline-first Python assistant with local conversation memory, a searchable knowledge base, optional Ollama/OpenAI-compatible model backends, and a Windows desktop GUI.**

> **Development status:** This repository is under active development. The latest GitHub Actions run on `main` (14 November 2026) compiled successfully but failed during the unit-test step on Python 3.10–3.13. Do not treat the current branch as a verified stable release.

## What is in the repository?

| Component | Current status | Description |
| --- | --- | --- |
| `ruller_ai/` | Main runnable application | CLI, Tkinter GUI, local memory, knowledge retrieval, adaptive examples, provider integration, and allowlisted tools. |
| `tests/` | Test suite | Unit tests for the main `ruller_ai` package. Current CI is failing; see status above. |
| `omniagent/` | Experimental prototype | Separate local-first orchestration prototype with provider, routing, SQLite session, and plugin-registry modules. It is not included in the configured install package or current CI test matrix. |
| `docs/` | Project documentation | Architecture, security, built-in tools, roadmap, and data-ingestion notes. |

The installable package is `ruller_ai`. The `omniagent` directory is exploratory code and should not be assumed to have feature parity with the main assistant.

## Features in the main application

- Offline-first operation with local conversation memory and local knowledge retrieval.
- Optional Ollama local-model integration.
- Optional OpenAI-compatible hosted-model integration.
- Windows desktop GUI built with Tkinter.
- User-approved examples and feedback for retrieval/prompt context (not model-weight training).
- Opt-in capture of future ordinary chat messages into the local knowledge base.
- Explicit DuckDuckGo web search; optional saving of returned snippets to local knowledge.
- Local text/CSV ingestion and searchable notes.
- Safe arithmetic evaluation and deterministic date, time, and unit-conversion tools.
- Allowlisted tool registry; arbitrary shell and Python execution are not exposed by the built-in tool system.

## Requirements

- Python **3.10 or newer**.
- Windows, Linux, or macOS for the Python CLI; the documented desktop experience targets Windows.
- No mandatory third-party runtime dependencies for the core package.
- Ollama is optional and must be installed separately for local model inference.
- Hosted model use requires a compatible provider endpoint and API key.
- Optional image OCR requires the Python packages `pillow` and `pytesseract`, plus the Tesseract OCR application installed on the operating system. OCR is not required for normal assistant use.

## Installation (Windows PowerShell)

Clone the repository and enter its directory:

```powershell
git clone https://github.com/ShivayCodes/U.L.T.R.O.N-1.0.git
Set-Location U.L.T.R.O.N-1.0
```

Create an isolated virtual environment and install the project in editable mode:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

Activation is optional. Using the virtual-environment interpreter directly avoids PowerShell execution-policy changes and keeps dependencies isolated.

## Launch and usage

### Start the command-line assistant

```powershell
.\.venv\Scripts\python.exe -m ruller_ai
```

### Start the desktop GUI

```powershell
.\.venv\Scripts\python.exe -m ruller_ai --gui
```

An optional `run_ultron_gui.bat` launcher is also present in the repository. If Windows blocks batch launchers, use the PowerShell command above.

### Choose a data directory

By default, ULTRON stores its local data under `%USERPROFILE%\.ruller_ai` on Windows. To use a project-specific directory:

```powershell
.\.venv\Scripts\python.exe -m ruller_ai --gui --data-dir .\ultron-data
```

### Select a model backend

**Offline (default):** no model provider is called. ULTRON uses its local retrieval and built-in functionality.

**Local with Ollama:** install and start Ollama separately, then pull a model:

```powershell
ollama pull llama3.1
$env:ULTRON_PROVIDER = "ollama"
$env:ULTRON_MODEL = "llama3.1"
.\.venv\Scripts\python.exe -m ruller_ai --gui
```

You can also select the provider in the GUI settings.

**Hosted OpenAI-compatible endpoint:** choose the OpenAI provider in the GUI and provide the API key in the application settings, or set it in the current PowerShell session before starting the CLI:

```powershell
$env:ULTRON_PROVIDER = "openai"
$env:ULTRON_MODEL = "gpt-4o-mini"
$env:OPENAI_API_KEY = "YOUR_API_KEY"
# Optional: use a compatible HTTPS endpoint other than the default
$env:OPENAI_API_BASE = "https://your-provider.example/v1"
.\.venv\Scripts\python.exe -m ruller_ai
```

Use a secure secret manager or session-scoped environment variable; do not commit API keys, paste them into source files, or put them in command-line arguments. Remove the key from the current PowerShell session when finished:

```powershell
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
```

The GUI requires explicit hosted-model consent before sending chat prompts to a remote provider. Remote endpoints must use HTTPS. HTTP is accepted only for loopback endpoints without an API key. Provider redirects are not followed.

## Help and command reference

Type `/help` in the CLI or GUI chat input to display the in-app help. Commands are entered as text in the chat composer.

| Command | Usage | Purpose |
| --- | --- | --- |
| Help | `/help` | Show the command menu. |
| Backend | `/model` | Show the configured model provider and whether it is active. |
| Teach | `/teach QUESTION => ANSWER` | Save a user-approved question/answer example for future retrieval and prompt context. |
| Feedback | `/feedback helpful` | Rate the last ordinary answer as helpful. |
| Feedback with note | `/feedback not-helpful Please explain the steps` | Rate the last answer and save an optional improvement note. |
| Learning status | `/learning status` | Show example/feedback counts and auto-learning state. |
| Clear learned examples | `/learning forget all` | Delete approved examples and feedback; does not delete conversation memory or knowledge documents. |
| Add knowledge | `/learn TEXT` | Save a text note to the local knowledge base. |
| Search knowledge | `/search QUERY` | Search locally stored knowledge. |
| Import a file | `/ingest PATH` | Import a supported local text or CSV file. |
| Auto-learning | `/autolearn on` | Opt in to adding future ordinary chat messages to local knowledge. |
| Disable auto-learning | `/autolearn off` | Stop future automatic capture; existing data remains. |
| Auto-learning status | `/autolearn status` | Show whether automatic capture is enabled. |
| Web search | `/web QUERY` | Search DuckDuckGo and show results without saving them. |
| Research | `/research QUERY` | Search DuckDuckGo and save returned snippets locally; verify sources and dates. |
| Remember a note | `/remember NOTE` | Add a note to local conversation memory. |
| Calculator | `/calc EXPRESSION` | Safely evaluate supported arithmetic expressions. |
| Unit conversion | `/convert 10 km to miles` | Convert supported length, mass, time, or temperature units. |
| Date | `/date today` | Show a date. Also supports `tomorrow`, `yesterday`, `in N days`, and `N weeks ago`. |
| Time | `/time` | Show the local system time. |
| Tool list | `/tool list` | List registered built-in tools, permissions, inputs, and side-effect descriptions. |
| Tool status | `/tool status` | Show tool permission counts and execution restrictions. |
| Statistics | `/stats` | Show local data counts. |
| Clear conversation | `/clear` | Clear conversation memory only; knowledge and learned examples remain. |
| Exit CLI | `/exit` | Close the command-line assistant. |

### Example session

```text
/help
/learn Python lists store ordered items.
/search Python lists
/teach What is a list in Python? => A list is an ordered, mutable collection.
/learning status
/calc (12 + 8) * 3
/convert 100 km to miles
/date tomorrow
/time
/exit
```

## GUI help

The desktop interface includes a chat composer, backend selection, model configuration, an API-key field, hosted-model consent, backend health check, and shortcuts for Offline / Local / Online modes. Use the command list in the sidebar to insert a command into the composer. Press Enter or select Send to submit a message.

The backend health check checks local Ollama availability/model presence or requests the compatible API's `/models` endpoint. Some compatible services do not expose that endpoint. A failed health check does not necessarily mean chat completions are unavailable; it does not send a chat prompt or guarantee future availability.

## Adaptive learning: what it does and does not do

ULTRON does **not** train model weights, fine-tune a model, or autonomously rewrite its source code.

- `/teach` saves examples explicitly approved by the user.
- `/feedback` stores a rating and optional correction note.
- Relevant examples and notes may be added to a model prompt when a provider is configured.
- `/autolearn on` opts in to storing future ordinary chat messages in local knowledge.
- `/learning forget all` clears examples and feedback.
- `/clear` clears conversation memory only.

Review saved information before enabling hosted mode. Relevant examples or feedback notes may be transmitted with a prompt to the selected remote provider after GUI consent.

## Privacy and security

- Offline mode does not call a model provider. Explicit `/web` and `/research` commands send search queries to DuckDuckGo.
- Local conversation data and knowledge are stored in the selected data directory. The default Windows location is `%USERPROFILE%\.ruller_ai`.
- Hosted prompts are sent only when a hosted provider is selected; the GUI additionally requires session consent.
- API URLs and model identifiers are validated; request sizes and timeouts are bounded; provider redirects are blocked.
- API keys must not be placed in source control or command-line arguments.
- The memory SHA-256 sidecar can detect accidental or one-sided edits. It is **not** authenticated protection against a process or account that can modify both the data and its guard file.
- Prompt-injection defenses and credential redaction are best-effort controls, not guarantees. Do not submit passwords, API keys, private tokens, or confidential data.
- Built-in tools are explicitly registered and do not provide arbitrary shell or Python execution.

Read [Security notes](docs/SECURITY.md) before configuring a hosted provider.

## Development and tests

Install the project and run the checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m compileall -q ruller_ai tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The GitHub Actions workflow is configured for Python 3.10, 3.11, 3.12, and 3.13. The latest run on the current `main` commit completed compilation but failed at the unit-test step across the matrix. The CLI smoke-test step was skipped because the tests failed first. Resolve the failing tests and obtain a green CI run before treating the repository as release-ready.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Built-in tools and permissions](docs/BUILTIN_TOOLS.md)
- [Security notes](docs/SECURITY.md)
- [CSV dataset ingestion](docs/CSV_DATASET_INGESTION.md)
- [Product roadmap](docs/PRODUCT_ROADMAP.md)
- [Project requirements](PRD.md)

## License

See [LICENSE](LICENSE).
