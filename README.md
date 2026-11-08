# ULTRON 1.0

**A Python AI assistant with local memory, optional model backends, and a Windows desktop GUI.**

## Windows GUI

Install Python 3.10+ with Tcl/Tk, then double-click `run_ultron_gui.bat` or launch from PowerShell:

```powershell
py -3 -m ruller_ai --gui
```

The chat composer is pinned to the bottom of the window. Type a message and press Enter or select **Send**. The sidebar includes a visible command-help list; double-click a command to place it in the composer.

## Model modes and health checks

Use the sidebar's **Offline**, **Local**, and **Online** buttons for one-click mode switching:

- **Offline** uses only local retrieval; no model network request is made.
- **Local** selects Ollama and defaults to `llama3.1`. Install Ollama and pull the model first (for example `ollama pull llama3.1`).
- **Online** selects an OpenAI-compatible provider (default model `gpt-4o-mini`); provide an API key and HTTPS API base where needed.

Select **Check backend** to test configured provider availability without generating a chat completion. Ollama checks that its local service and selected model are present. OpenAI-compatible providers request the endpoint's `/models` list. Some compatible services do not implement that route; in that case, health check can fail even if completions work. A health check does not guarantee future requests will succeed.

For safety, remote APIs must use HTTPS. HTTP is accepted only for localhost/loopback endpoints. API keys entered in the GUI are held in memory only for this process.

## CLI and setup

```powershell
py -3 -m pip install -e .
py -3 -m ruller_ai
py -3 -m ruller_ai --gui --data-dir .\ultron-data
```

Set an Ollama default from PowerShell:

```powershell
$env:ULTRON_PROVIDER = "ollama"
$env:ULTRON_MODEL = "llama3.1"
py -3 -m ruller_ai --gui
```

For OpenAI-compatible services, enter the key in the GUI or set `OPENAI_API_KEY`. Never pass secrets as command-line options.

## Commands / help

Type `/help` in the GUI composer or CLI. Commands include `/model`, `/teach QUESTION => ANSWER`, `/feedback helpful|not-helpful [NOTE]`, `/learning status`, `/learning forget all`, `/learn TEXT`, `/search QUERY`, `/ingest PATH`, `/web QUERY`, `/research QUERY`, `/remember NOTE`, `/autolearn on|off|status`, `/calc EXPRESSION`, `/convert`, `/date`, `/time`, `/tool list`, `/tool status`, `/stats`, and `/clear`. See the in-app command-help panel for descriptions. `/clear` clears conversation memory but preserves knowledge and approved learning examples.

## Safe adaptive learning

ULTRON does not train model weights or rewrite itself. `/teach` stores user-approved examples for local retrieval and bounded model prompt context. `/feedback` records a user rating and optional note; feedback notes may be sent to a configured hosted model when included in a prompt. `/learning forget all` erases examples and feedback. `/autolearn` is a separate opt-in that stores future ordinary messages to local knowledge.

## Privacy and tests

Local data is stored under `%USERPROFILE%\\.ruller_ai` on Windows. Hosted prompts go to the configured model provider; `/web` and `/research` queries go to DuckDuckGo. Avoid sending confidential information to external services. The adjacent memory SHA-256 sidecar detects accidental or one-sided edits, not malicious tampering by someone with same-account write access. See [Security notes](docs/SECURITY.md).

```powershell
py -3 -m compileall -q ruller_ai tests
py -3 -m unittest discover -s tests -v
```
