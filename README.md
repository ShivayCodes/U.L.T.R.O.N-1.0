# U.L.T.R.O.N 1.0

**A Python AI assistant with local memory, model backends, and a Windows-friendly graphical interface.**

ULTRON combines local conversation memory and knowledge retrieval with optional Ollama or OpenAI-compatible AI models. The desktop app uses Python's built-in Tkinter toolkit, so no additional GUI package is required.

## Windows desktop app

1. Install Python 3.10 or newer and enable **Add Python to PATH** in the installer.
2. Download or clone this repository and open its folder.
3. Double-click `run_ultron_gui.bat`.

Alternatively, from PowerShell in the project folder:

```powershell
py -3 -m pip install -e .
ultron-gui
```

You can also launch the GUI from the module:

```powershell
py -3 -m ruller_ai --gui
```

The GUI starts in offline mode by default. In the **Model settings** sidebar choose `ollama` or `openai`, enter the model name, add API settings if needed, then select **Apply settings**. Ollama must be installed and running locally. For hosted OpenAI-compatible services, enter the endpoint and API key; keys remain in memory for the current app session and are not written to the data files.

## Command-line mode

The existing terminal interface is still available:

```powershell
py -3 -m ruller_ai
```

## Features

- Windows desktop chat with chat bubbles, timestamps, a live thinking spinner, and a dark-mode toggle
- Sidebar for provider, model, API endpoint, and API-key configuration
- Optional real model providers (Ollama and OpenAI-compatible HTTP APIs)
- Local conversation memory and persistent knowledge search
- Explicit web search and optional user-directed local saving
- Offline local-retrieval fallback if no model is configured
- Safe arithmetic evaluation using an AST allowlist, not `eval()` or `exec()`

## Chat commands

The GUI accepts the same messages and slash commands as the CLI: `/help`, `/model`, `/learn TEXT`, `/search QUERY`, `/web QUERY`, `/research QUERY`, `/ingest PATH`, `/stats`, and `/clear`. `/clear` asks for confirmation, clears conversation memory, and preserves local knowledge.

## Data and privacy

Conversation history and learned knowledge are stored locally under `%USERPROFILE%\\.ruller_ai` on Windows (or `~/.ruller_ai` on other platforms). When using a hosted model, prompts are sent to that provider. Avoid submitting secrets or sensitive data to remote providers or web search. The GUI does not persist API keys.

## Tests

```powershell
py -3 -m compileall -q ruller_ai tests
py -3 -m unittest discover -s tests -v
```

The GUI requires a Python installation that includes Tkinter. Standard Windows Python installers usually include it.
