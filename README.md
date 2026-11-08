# ULTRON 1.0

**A Python AI assistant with local memory, optional model backends, and a Windows desktop GUI.**

## Windows GUI

Install Python 3.10+ with Tcl/Tk, then double-click `run_ultron_gui.bat` or launch from PowerShell:

```powershell
py -3 -m ruller_ai --gui
```

The chat composer stays pinned at the bottom. Enter a message and press Enter or click Send. The sidebar provides an interactive command-help list, health checks, and Offline / Local / Online mode shortcuts.

## Security controls and backend modes

- **Offline** uses local retrieval only; no model provider is called.
- **Local** selects Ollama; install it and pull a model (e.g. `ollama pull llama3.1`).
- **Online** selects an OpenAI-compatible provider. You must explicitly check the hosted-model consent box before applying or sending prompts. Revoke consent to switch back offline.
- Remote APIs require HTTPS; HTTP is allowed only on loopback and never with an API key. API credentials are not accepted in command-line args. Redirects are not followed, which prevents prompt or authorization replay to a different endpoint.
- Provider configuration validates URL scheme, host, userinfo, query/fragment, model identifier, credential format, and bounded timeouts. Request prompt and response sizes are bounded. Provider failures are sanitized.
- GUI rejects oversized/control-character input before displaying or sending it. Chat prompts are sent to hosted services only after session consent; local conversation storage remains on the device.

The **Check backend** button checks Ollama availability/model presence or requests the compatible API `/models` endpoint. Some providers omit `/models`; such a check can fail even if completions work. It does not send a chat prompt or guarantee future availability.

## CLI and setup

```powershell
py -3 -m pip install -e .
py -3 -m ruller_ai
py -3 -m ruller_ai --gui --data-dir .\ultron-data
```

Set an Ollama default:

```powershell
$env:ULTRON_PROVIDER = "ollama"
$env:ULTRON_MODEL = "llama3.1"
py -3 -m ruller_ai --gui
```

For online use, enter the key in the GUI after checking consent, or set `OPENAI_API_KEY`. Never pass a secret as a command-line option or use an untrusted endpoint.

## Commands / help

Type `/help` in the GUI composer or CLI. Commands include `/model`, `/teach QUESTION => ANSWER`, `/feedback helpful|not-helpful [NOTE]`, `/learning status`, `/learning forget all`, `/learn TEXT`, `/search QUERY`, `/ingest PATH`, `/web QUERY`, `/research QUERY`, `/remember NOTE`, `/autolearn on|off|status`, `/calc EXPRESSION`, `/convert`, `/date`, `/time`, `/tool list`, `/tool status`, `/stats`, and `/clear`. Double-click an item in the GUI command list to insert it into the composer.

## Adaptive learning

ULTRON does not train model weights or rewrite itself. `/teach` stores user-approved examples for local retrieval and bounded model prompt context. `/feedback` records a user rating and optional note; notes may be sent to a configured hosted provider only after online consent. `/learning forget all` erases examples and feedback. `/autolearn` is a separate opt-in for adding future chat messages to local knowledge.

## Privacy and limitations

Local data is stored under `%USERPROFILE%\\.ruller_ai` on Windows. Hosted prompts and any included approved examples/feedback notes go to the configured provider only while online mode is explicitly enabled. `/web` and `/research` queries go to DuckDuckGo. Don't submit secrets or confidential data. The memory SHA-256 sidecar detects accidental/one-sided edits, not malicious tampering by someone with same-account write access. No software can promise protection from all exploitation or leaks; keep the OS/Python updated and secure your device.

## Tests

```powershell
py -3 -m compileall -q ruller_ai tests
py -3 -m unittest discover -s tests -v
```
