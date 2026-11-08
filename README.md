# U.L.T.R.O.N 1.0

**A Python AI assistant with local memory, model backends, and a Windows-friendly graphical interface.**

ULTRON combines local conversation memory and knowledge retrieval with optional Ollama or OpenAI-compatible AI models. The desktop app uses Python's built-in Tkinter toolkit.

## Windows desktop app

1. Install Python 3.10 or newer and enable **Add Python to PATH**.
2. Download or clone this repository and open its folder.
3. Double-click `run_ultron_gui.bat`, or run `py -3 -m ruller_ai --gui` in PowerShell.

To install the `ultron-gui` command, run `py -3 -m pip install -e .` and then `ultron-gui`.

The GUI starts offline. In the model settings sidebar select `ollama` or `openai`, enter the model and endpoint, and apply settings. Ollama must be installed locally. API keys entered in the GUI are held only for the current process.

## Command-line mode

```powershell
py -3 -m ruller_ai
```

Configure hosted credentials using `OPENAI_API_KEY` / `ULTRON_API_KEY`, or use the hidden CLI prompt when selecting OpenAI. Do not put credentials in command-line arguments. Remote model endpoints require HTTPS; HTTP is accepted only for localhost/loopback services.

## Features

- Windows desktop chat with chat bubbles, timestamps, dark mode, and a thinking spinner
- Sidebar settings for provider, model, API endpoint, and API key
- Ollama and OpenAI-compatible model providers with local fallback
- Local conversation memory and persistent knowledge search
- Explicit web search and user-directed local saving
- Safe arithmetic evaluation using an AST allowlist, not `eval()` or `exec()`

## Chat commands

The GUI accepts `/help`, `/model`, `/learn TEXT`, `/search QUERY`, `/web QUERY`, `/research QUERY`, `/ingest PATH`, `/stats`, and `/clear`. `/clear` clears conversation memory and preserves local knowledge.

## Data and privacy

Conversation history and learned knowledge are stored under `%USERPROFILE%\\.ruller_ai` on Windows (or `~/.ruller_ai` elsewhere). Hosted model prompts are sent to the configured provider. Avoid submitting secrets or sensitive data to remote providers or web search. The memory SHA-256 sidecar detects accidental or one-sided changes only; it is not malicious-tampering protection. See [Security notes](docs/SECURITY.md).

## Tests

```powershell
py -3 -m compileall -q ruller_ai tests
py -3 -m unittest discover -s tests -v
```

The GUI requires a Python installation that includes Tkinter. Standard Windows Python installers usually include it.
