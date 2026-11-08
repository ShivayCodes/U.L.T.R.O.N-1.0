# ULTRON 1.0

**A Python AI assistant with local memory, optional model backends, and a Windows desktop GUI.**

The GUI is built with Python's Tkinter standard library. It supports offline local retrieval or optional Ollama and OpenAI-compatible models. Network model requests are sent only when a model backend is configured.

## Windows: launch the graphical app

1. Install Python 3.10+ and enable **Add Python to PATH**. Make sure the Python install includes Tcl/Tk (the normal python.org Windows installer does).
2. Download/clone this repo and open the project folder.
3. Double-click `run_ultron_gui.bat`.

Or use PowerShell in the repository folder:

```powershell
py -3 -m ruller_ai --gui
```

To install a desktop command:

```powershell
py -3 -m pip install -e .
ultron-gui
```

The chat input is the fixed bar at the **bottom of the right-hand Chat panel**. Click “Type your message here…”, enter a message, then press **Enter** or click **Send**. The app shows a thinking indicator while processing. Commands are typed into the same box.

## Configure a model in the GUI

- **Offline:** choose `offline`; local knowledge lookup still works, but there is no general-purpose model.
- **Ollama:** install and start Ollama, then choose `ollama` and set a model name (for example `llama3.1`). Apply settings. Requests run locally through Ollama.
- **OpenAI-compatible:** choose `openai`, set the model name (for example `gpt-4o-mini`), enter an HTTPS API base URL if using a non-default compatible service, and enter the API key. Click **Apply settings**. Keys entered in the GUI remain in memory for the current process only.

Remote endpoints must use HTTPS. HTTP is allowed only for `localhost` and loopback IPs for local model servers. Never share API keys or send them through untrusted endpoints.

## Command-line mode

Run the existing terminal UI:

```powershell
py -3 -m ruller_ai
```

Run GUI with a data folder:

```powershell
py -3 -m ruller_ai --gui --data-dir .\ultron-data
```

Set a model provider without putting a key in command history:

```powershell
$env:ULTRON_PROVIDER = "ollama"
$env:ULTRON_MODEL = "llama3.1"
py -3 -m ruller_ai --gui
```

For an OpenAI-compatible provider, prefer environment variables or enter the key in the GUI:

```powershell
$env:ULTRON_PROVIDER = "openai"
$env:ULTRON_MODEL = "gpt-4o-mini"
$env:OPENAI_API_KEY = Read-Host "API key"
py -3 -m ruller_ai
```

Do **not** put a credential in a command-line argument: process listings and shell history may expose it. The CLI asks for a hidden key if OpenAI is selected and no key is set in the environment.

## Chat commands / help

Type `/help` in the GUI chat box or CLI to print the built-in command list.

| Command | What it does |
|---|---|
| `/help` | Display all built-in commands |
| `/model` | Show the configured model backend status |
| `/learn TEXT` | Add a passage to local searchable knowledge |
| `/search QUERY` | Search stored local knowledge and show source attribution |
| `/ingest PATH` | Import supported local text or CSV data (size limits apply) |
| `/web QUERY` | Search DuckDuckGo on request; results are not saved |
| `/research QUERY` | Search the web and save returned snippets locally |
| `/remember NOTE` | Save a note to local conversation memory |
| `/autolearn on\|off\|status` | Explicitly opt in/out of saving future chat messages to knowledge |
| `/calc EXPRESSION` | Safely evaluate basic arithmetic using an AST allowlist |
| `/convert VALUE UNIT to UNIT` | Convert supported units |
| `/date today` | Show the current local date; relative date forms are supported |
| `/time` | Show local system time |
| `/tool list` / `/tool status` | Inspect built-in tool permissions |
| `/stats` | Show local memory/knowledge counts and data paths |
| `/clear` | Clear conversation memory only; learned knowledge is preserved |
| `/exit` | Exit CLI (close the window to quit GUI) |

## Privacy and limitations

Memory and knowledge are stored locally under `%USERPROFILE%\\.ruller_ai` on Windows (or `~/.ruller_ai` elsewhere). Hosted model prompts are sent to the configured provider; explicit web-search queries go to DuckDuckGo. Avoid sending confidential information to remote services. The adjacent memory SHA-256 sidecar detects accidental or one-sided edits; it is **not** a malicious-tampering boundary against someone with access to the same account. See [Security notes](docs/SECURITY.md).

## Tests

From the repository root:

```powershell
py -3 -m compileall -q ruller_ai tests
py -3 -m unittest discover -s tests -v
```

The GUI requires an available desktop session; tests can run headlessly without opening a window. Standard Windows Python installations typically include Tkinter.
