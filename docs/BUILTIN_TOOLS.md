# Built-in tools and permissions

U.L.T.R.O.N exposes a small registry of deterministic, local-only tools. Tools are
explicitly registered; user input is never evaluated as Python or passed to a
shell. Current tools are read-only and classified `SAFE`, so they run without a
confirmation prompt:

- `/time` — show the local system time.
- `/date [today|tomorrow|yesterday|in N days|N weeks ago]` — show a local date.
- `/convert AMOUNT UNIT to UNIT` — convert supported length, mass, time, or
temperature units (for example, `/convert 10 km to miles`).
- `/tool list` and `/tool status` — inspect registered tool metadata and policy.

Each tool declares a name, description, input schema, permission class, and
side-effect summary. The registry checks permission before execution and writes
an audit log containing only tool name, permission class, and outcome; input
arguments and exception text are excluded to avoid logging private data. Logs
use Python's standard `ruller_ai.tools` logger and are silent at the default
logging level unless the application configures INFO logging.

Permission classes are `SAFE` (automatic, read-only), `LIMITED` and `CONFIRM`
(explicit confirmation required by the registry), and `BLOCKED` (never runs).
No current tool has write, destructive, shell, Python-execution, or network
side effects. Any future side-effecting tool must be explicitly registered,
validated, and require confirmation or remain blocked.
