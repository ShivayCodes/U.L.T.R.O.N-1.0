# ULTRON 1.0

**A Python AI assistant with local memory, optional model backends, and a Windows desktop GUI.**

The GUI uses Python's Tkinter standard library. ULTRON supports offline local retrieval or optional Ollama and OpenAI-compatible models. Network model requests are sent only when a model backend is configured.

## Windows: launch the graphical app

1. Install Python 3.10+ and enable **Add Python to PATH**. Ensure Tcl/Tk is installed (normally included in python.org's Windows installer).
2. Download or clone this repository and open its folder.
3. Double-click `run_ultron_gui.bat`, or run in PowerShell:

```powershell
py -3 -m ruller_ai --gui
```

To install and start the desktop command:

```powershell
py -3 -m pip install -e .
ultron-gui
```

Type into the input bar at the **bottom of the right-hand Chat panel**. Press **Enter** or click **Send**. `/help` displays chat commands. The progress bar shows when ULTRON is working.

## Configure a model

- **Offline:** choose `offline`; local knowledge lookup works, but this is not a general language model.
- **Ollama:** install and start Ollama, choose `ollama`, enter an installed model name such as `llama3.1`, and apply settings.
- **OpenAI-compatible:** choose `openai`, set a model name and (if needed) HTTPS API base URL, enter the API key, then apply settings. GUI keys are kept in process memory only.

Remote endpoints must use HTTPS. HTTP is accepted only for localhost/loopback model services. Never use an untrusted endpoint for credentials.

## Command-line mode

```powershell
py -3 -m ruller_ai
py -3 -m ruller_ai --gui --data-dir .\ultron-data
```

Configure local Ollama in PowerShell:

```powershell
$env:ULTRON_PROVIDER = "ollama"
$env:ULTRON_MODEL = "llama3.1"
py -3 -m ruller_ai --gui
```

For hosted providers, use the GUI key field, or set environment variables. Do not pass keys as CLI arguments:

```powershell
$env:ULTRON_PROVIDER = "openai"
$env:ULTRON_MODEL = "gpt-4o-mini"
$env:OPENAI_API_KEY = Read-Host "API key"
py -3 -m ruller_ai
```

## Safe adaptive learning

ULTRON does not train model weights or autonomously rewrite itself. Its transparent, user-controlled learning adds reviewed examples to local storage, retrieves relevant examples for later questions, and records optional answer feedback. Feedback notes can be included in a configured model prompt; with a hosted service, prompt context is sent to that provider. Review examples before relying on them and do not teach secrets.

Examples in the GUI chat box or CLI:

```text
/teach How do I reset the local index? => Use /clear only to clear conversation memory; knowledge is retained.
/feedback helpful
/feedback not-helpful Please distinguish memory clearing from deleting learned knowledge.
/learning status
/learning forget all
```

`/teach QUESTION => APPROVED ANSWER` saves or updates a user-reviewed example. Matching examples guide offline retrieval and are supplied as bounded context to a configured model. `/feedback helpful` or `/feedback not-helpful [note]` rates your last ordinary chat answer; the optional note may guide future replies but never trains the model. `/learning forget all` erases examples and feedback (not conversation memory or the knowledge base). Legacy `/autolearn on` remains opt-in and adds future ordinary messages to local knowledge; it is separate from model training.

## Chat commands / help

Type `/help` in the GUI input box or CLI:

| Command | Purpose |
|---|---|
| `/help` | Show all commands |
| `/model` | Show backend status |
| `/teach QUESTION => ANSWER` | Save an explicitly approved example |
| `/feedback helpful\|not-helpful [NOTE]` | Rate last ordinary answer, optionally add guidance |
| `/learning status` | Show approved-example and feedback counts |
| `/learning forget all` | Delete adaptation examples and feedback |
| `/learn TEXT` | Add text to local searchable knowledge |
| `/search QUERY` | Search local knowledge and show source attribution |
| `/ingest PATH` | Import supported local text or CSV data within size limits |
| `/web QUERY` | Search DuckDuckGo on request, without saving results |
| `/research QUERY` | Search and save returned snippets locally |
| `/remember NOTE` | Save a note to local conversation memory |
| `/autolearn on\|off\|status` | Opt into/out of storing future chat messages in local knowledge |
| `/calc EXPRESSION` | Safely evaluate arithmetic (AST allowlist) |
| `/convert VALUE UNIT to UNIT`, `/date today`, `/time` | Use safe local utilities |
| `/tool list`, `/tool status` | Inspect built-in tool permissions |
| `/stats` | Show local data counts and paths |
| `/clear` | Clear conversation memory, preserve knowledge and approved examples |
| `/exit` | Exit CLI; close the GUI window to quit |

## Data, privacy, and limits

Local data is stored under `%USERPROFILE%\\.ruller_ai` on Windows or `~/.ruller_ai` elsewhere. Hosted prompts and any included matching examples/feedback notes go to the configured model provider. Explicit web queries go to DuckDuckGo. Do not send sensitive information to external providers. The memory SHA-256 sidecar detects accidental or one-sided edits; it is not a malicious-tampering boundary. See [Security notes](docs/SECURITY.md).

## Tests

From the repository root:

```powershell
py -3 -m compileall -q ruller_ai tests
py -3 -m unittest discover -s tests -v
```
