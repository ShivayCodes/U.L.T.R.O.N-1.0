# U.L.T.R.O.N 1.0

**Beyond Conventional AI. Toward Adaptive Intelligence.**

U.L.T.R.O.N 1.0 is an offline-first Python assistant prototype with local conversation memory, a knowledge base, explainable text retrieval, and a constrained arithmetic tool. Optional web search runs only when explicitly requested. It is not a trained language model and does not claim AGI or autonomous self-improvement.

## Features

- Python 3.10+ and no third-party runtime dependencies
- Bounded local conversation memory and local knowledge storage
- Explicit opt-in conversation learning (`/autolearn on`)
- Knowledge ingestion from supported local text files
- Explainable lexical retrieval with source attribution
- Explicit DuckDuckGo web lookup (`/web`) and user-directed saving (`/research`)
- Safe calculator that uses an AST allowlist, not `eval()` or `exec()`

## Install

Install Python 3.10 or newer. From a terminal, clone the repository and install it in an isolated environment.

**Windows PowerShell**

```powershell
git clone https://github.com/ShivayCodes/U.L.T.R.O.N-1.0.git
cd U.L.T.R.O.N-1.0
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

**macOS / Linux**

```bash
git clone https://github.com/ShivayCodes/U.L.T.R.O.N-1.0.git
cd U.L.T.R.O.N-1.0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The editable install makes the `ruller-ai` command available. Alternatively, run the package without installing it with `python -m ruller_ai` from the repository root. Do not execute `ruller_ai/cli.py` directly; it relies on package-relative imports.

## Run and use

Start the assistant:

```bash
ruller-ai
```

Or choose a custom location for local data:

```bash
python -m ruller_ai --data-dir ./ruller-data
```

Example session:

```text
You> /help
You> /calc 12 * (3 + 2)
You> /learn Python supports automation and data analysis.
You> /search Python automation
You> /web latest Python release
You> /research Python 3.13 release notes
You> /autolearn on
You> A note I want the assistant to learn for future local retrieval.
You> /autolearn off
You> /stats
You> /exit
```

| Command | Purpose |
|---|---|
| `/help` | Show available commands |
| `/calc EXPRESSION` | Safely calculate basic arithmetic |
| `/learn TEXT` | Add a passage to the local knowledge base |
| `/search QUERY` | Search locally stored passages |
| `/ingest PATH` | Import a supported local text file up to 1 MB |
| `/remember NOTE` | Store a note in local conversation memory |
| `/autolearn on\|off\|status` | Opt in/out of adding future ordinary messages to local knowledge |
| `/web QUERY` | Search DuckDuckGo; display results without saving them |
| `/research QUERY` | Search DuckDuckGo and save returned snippets with source URLs locally |
| `/stats` | Show memory, knowledge, and data-directory information |
| `/time` | Show local system time |
| `/clear` | Clear conversation memory; knowledge is retained |
| `/exit` | Quit the CLI |

## Memory, learning, and web lookup

Conversation history is stored locally with a configurable item limit; it is not literally unlimited. Ordinary messages are already retained in bounded conversation memory. `/autolearn` is **off by default**; when enabled, future ordinary messages are additionally added to the local knowledge base for retrieval. This does not train or modify a model. Disable it with `/autolearn off`. `/clear` clears conversation memory, not learned knowledge.

The app does not search the internet in the background. `/web` sends the provided query to DuckDuckGo and shows result titles, snippets, and source URLs; it does not open result pages or save the results. `/research` explicitly saves those returned snippets to local knowledge. Search output can be incomplete, stale, or misleading; verify the linked sources. Avoid entering sensitive information into web searches. No Google account, API key, or external model is required.

Data defaults to `~/.ruller_ai/`. Treat memory and knowledge as personal data; do not ingest secrets or material you do not have permission to use.

## Tests

The test suite uses Python's standard library:

```bash
python -m compileall -q ruller_ai tests
python -m unittest discover -s tests -v
```

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
  web_search.py
tests/
  test_core.py
  test_cli.py
  test_learning_web.py
docs/
  ARCHITECTURE.md
pyproject.toml
```

See [Architecture and limitations](docs/ARCHITECTURE.md) for implementation details and limitations.
