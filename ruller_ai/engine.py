"""Orchestrates local memory, knowledge retrieval, web lookup, and responses."""
import json
import logging
from datetime import datetime
from pathlib import Path

from .config import Settings
from .knowledge import KnowledgeBase
from .memory import MemoryStore
from .providers import ProviderError, build_provider
from .reasoning import UnsafeExpression, safe_calculate
from .security import (
    InputValidationError,
    contains_sensitive_value,
    redact_secrets,
    secure_system_instructions,
    validate_chat_input,
    validate_model_output,
)
from .storage import read_json, write_json
from .tools import Permission, ToolError, create_builtin_registry
from .web_search import search_web

logger = logging.getLogger(__name__)


class RullerAI:
    """Offline-first assistant with optional live model support."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory = MemoryStore(self.settings.memory_file, self.settings.max_memory_items, self.settings.guard_file)
        self.knowledge = KnowledgeBase(self.settings.knowledge_file, self.settings.max_knowledge_items)
        self.learning_file = self.settings.data_dir / "learning.json"
        learning = read_json(self.learning_file, {})
        self._auto_learn_enabled = isinstance(learning, dict) and learning.get("enabled") is True
        self.provider = build_provider(
            self.settings.provider, model=self.settings.model,
            api_base=self.settings.api_base, api_key=self.settings.api_key,
        )
        self.system_prompt = secure_system_instructions(
            "You are ULTRON, a helpful AI assistant. Use local knowledge and web sources "
            "when needed, and clearly state uncertainty when the answer is not reliable."
        )
        self.tools = create_builtin_registry()
        self._provider_failure: str | None = None

    def _model_answer(self, prompt: str) -> str | None:
        self._provider_failure = None
        if self.provider is None:
            return None
        if contains_sensitive_value(prompt):
            self._provider_failure = "Potential credentials detected; remote model transmission was blocked."
            logger.warning("Model request blocked because the prompt matched a sensitive-value pattern.")
            return None
        try:
            return validate_model_output(
                self.provider.generate(prompt, system_prompt=self.system_prompt, max_tokens=512)
            )
        except ProviderError as exc:
            self._provider_failure = redact_secrets(str(exc))
            logger.warning("Model request failed safely: %s", self._provider_failure)
        except Exception as exc:
            self._provider_failure = "Unexpected provider error. Check local diagnostics."
            logger.warning("Model request failed unexpectedly (%s).", type(exc).__name__)
        return None

    def chat(self, message: str) -> str:
        try:
            text = validate_chat_input(message, max_chars=self.settings.max_input_chars)
        except InputValidationError as exc:
            return str(exc)
        if not text:
            return "Please enter a message."

        # Persist a redacted copy; never write obvious credential assignments to chat history.
        self.memory.add("user", redact_secrets(text))
        lowered = text.casefold()

        if lowered in {"/help", "help"}:
            answer = self.help_text()
        elif lowered in {"/time", "what time is it", "what is the time"}:
            answer = self._run_tool("time")
        elif lowered == "/date" or lowered.startswith("/date "):
            answer = self._run_tool("date", text[len("/date"):].strip())
        elif lowered.startswith("/convert "):
            answer = self._run_tool("convert", text[len("/convert "):].strip())
        elif lowered == "/tool" or lowered.startswith("/tool "):
            answer = self._tool_command(text[len("/tool"):].strip())
        elif lowered in {"/clear", "clear memory"}:
            self.memory.clear()
            answer = "Conversation memory cleared. Knowledge and saved web research were not changed."
        elif lowered.startswith("/calc "):
            answer = self._calculate(text[6:])
        elif lowered.startswith("/remember "):
            fact = text[len("/remember "):].strip()
            answer = "Tell me what to remember after /remember." if not fact else self._remember(fact)
        elif lowered.startswith("/learn "):
            fact = text[len("/learn "):].strip()
            if fact:
                added = self.knowledge.add_text(fact, "user note")
                answer = "Saved to the local knowledge base." if added else "That note is already in the knowledge base."
            else:
                answer = "Usage: /learn text you want to add"
        elif lowered.startswith("/search "):
            answer = self._search(text[8:])
        elif lowered.startswith("/ingest "):
            answer = self._ingest(text[8:])
        elif lowered.startswith("/autolearn"):
            answer = self._autolearn(text[len("/autolearn"):].strip())
        elif lowered.startswith("/web "):
            answer = self._web_lookup(text[5:].strip(), save=False)
        elif lowered.startswith("/research "):
            answer = self._web_lookup(text[len("/research"):].strip(), save=True)
        elif lowered in {"/stats", "stats"}:
            answer = self.stats()
        elif lowered in {"/model", "model"}:
            provider_name = self.provider.name if self.provider is not None else "offline"
            answer = f"Model provider: {provider_name}. Status: {'configured' if self.provider is not None else 'offline'}"
        elif lowered in {"hi", "hello", "hey", "hello ruller", "hi ruller"}:
            answer = "Hello! I'm ULTRON, your local assistant with optional real-model support. Ask a question, use /help, or teach me with /learn."
        else:
            answer = self._model_answer(text)
            if answer is None:
                answer = self._answer_from_knowledge(text)
                if self._provider_failure:
                    answer = f"Model request blocked or failed: {self._provider_failure}\n\nShowing local fallback:\n\n{answer}"
            if self._auto_learn_enabled and not text.startswith("/"):
                self.knowledge.add_text(redact_secrets(text), "opt-in conversation learning")
        answer = redact_secrets(answer)
        self.memory.add("assistant", answer)
        return answer

    @staticmethod
    def help_text() -> str:
        return (
            "ULTRON commands:\n"
            "  /help                 Show this help\n"
            "  /model                Show the active model provider status\n"
            "  /calc 12 * (3 + 2)    Safely calculate arithmetic\n"
            "  /learn some fact      Add text to local knowledge\n"
            "  /search keywords      Search local knowledge\n"
            "  /ingest path          Import a text file (max 1 MB) or CSV dataset (max 200 MB)\n"
            "  /remember a note      Save a note to conversation memory\n"
            "  /autolearn on|off     Opt in/out of saving future chat messages to knowledge\n"
            "  /convert 10 km to mi  Convert common local units (read-only)\n"
            "  /date tomorrow        Show a local relative date (read-only)\n"
            "  /tool list|status     Inspect built-in tools and permission policy\n"
            "  /web query            Search the web without saving results\n"
            "  /research query       Search the web and save returned snippets locally\n"
            "  /stats                Show local data counts\n"
            "  /time                 Show local system time\n"
            "  /clear                Clear conversation memory only\n"
            "When a model provider is available, it answers general questions before the local fallback.\n"
            "CSV rows are added to searchable local knowledge; this does not train a model.\n"
            "Web results are external and may be incomplete or inaccurate."
        )

    def _run_tool(self, name: str, argument: str = "") -> str:
        try:
            return self.tools.run(name, argument)
        except ToolError as exc:
            return f"Tool request rejected: {exc}"

    def _tool_command(self, command: str) -> str:
        option = command.casefold()
        tools = self.tools.list_tools()
        if option == "list":
            rows = ["Built-in tools (only explicitly registered tools can run):"]
            rows.extend(f"- {tool.name} [{tool.permission.value}]: {tool.description} Input: {tool.input_schema}. Side effects: {tool.side_effects}" for tool in tools)
            return "\n".join(rows)
        if option == "status":
            return (
                f"Registered built-in tools: {len(tools)}. "
                f"SAFE tools run automatically: {sum(tool.permission is Permission.SAFE for tool in tools)}. "
                f"Tools requiring confirmation: {sum(tool.permission in {Permission.LIMITED, Permission.CONFIRM} for tool in tools)}. "
                f"Blocked tools: {sum(tool.permission is Permission.BLOCKED for tool in tools)}. "
                "No arbitrary shell or Python execution is available."
            )
        return "Usage: /tool list | /tool status"

    def _autolearn(self, option: str) -> str:
        if option.casefold() == "status":
            return f"Opt-in conversation learning is {'on' if self._auto_learn_enabled else 'off'}."
        if option.casefold() not in {"on", "off"}:
            return "Usage: /autolearn on | /autolearn off | /autolearn status"
        self._auto_learn_enabled = option.casefold() == "on"
        write_json(self.learning_file, {"enabled": self._auto_learn_enabled})
        if self._auto_learn_enabled:
            return "Opt-in learning enabled. Future ordinary messages may be saved to the local knowledge base; existing history is unchanged."
        return "Opt-in learning disabled. Existing memory and knowledge were not deleted."

    def _web_lookup(self, query: str, *, save: bool) -> str:
        if not query:
            return f"Usage: {'/research' if save else '/web'} search terms"
        try:
            results = search_web(query, limit=5)
        except (OSError, RuntimeError, ValueError):
            return "Web lookup failed. Check connectivity and try again; diagnostic details were withheld."
        if not results:
            return "No web results were returned. Try a different query or use /search for local knowledge."
        lines = []
        for index, result in enumerate(results, 1):
            title, url, snippet = result["title"], redact_secrets(result["url"]), result["snippet"]
            lines.append(f"{index}. {title}\n   {snippet}\n   Source: {url}")
            if save:
                retrieved = datetime.now().astimezone().isoformat(timespec="seconds")
                self.knowledge.add_text(redact_secrets(f"{title}\n{snippet}\nRetrieved: {retrieved}"), url)
        heading = "Web results saved to local knowledge (verify sources and dates):\n" if save else "Web results (not saved):\n"
        return heading + "\n".join(lines)

    def _calculate(self, expression: str) -> str:
        try:
            return f"{expression.strip()} = {safe_calculate(expression)}"
        except UnsafeExpression as exc:
            return f"Calculation rejected: {exc}"

    def _remember(self, note: str) -> str:
        self.memory.add("system", "User note: " + redact_secrets(note))
        return "Saved that note in local memory."

    def _search(self, query: str) -> str:
        results = self.knowledge.search(query, limit=5)
        if not results:
            return "No matching local knowledge found. Add information with /learn, /ingest, or /research."
        return "\n".join(f"{i}. [{item['score']:.3f}] {item['text']} (source: {item['source']})" for i, item in enumerate(results, 1))

    def _answer_from_knowledge(self, query: str) -> str:
        results = self.knowledge.search(query, limit=3)
        if results:
            best = results[0]
            return (
                "I found a potentially relevant passage in your local knowledge base "
                f"(lexical match score {best['score']:.3f}):\n\n{best['text']}\n\n"
                f"Source: {best['source']}\nThis is retrieval, not proof that the passage is correct. Use /search for more matches."
            )
        prior = self.memory.search(query, limit=2)
        if prior:
            return (
                "I don't have a general-purpose language model connected, and found no matching knowledge. "
                f"A related prior conversation entry was: {prior[0].get('content', '')}\n\n"
                "Use /web to look up current sources, or add trusted information with /learn or /ingest."
            )
        return "I'm running in offline baseline mode, so I can't reliably answer open-ended questions yet. Use /web, /learn, or /ingest."

    def _ingest(self, raw_path: str) -> str:
        value = raw_path.strip().strip('"')
        if not value:
            return "Usage: /ingest path/to/file.txt or /ingest path/to/dataset.csv"
        path = Path(value).expanduser()
        try:
            added = self.knowledge.ingest_file(path)
        except ValueError as exc:
            return f"Import failed: {redact_secrets(str(exc))}"
        except (OSError, RuntimeError):
            return "Import failed. Check that the file exists, is supported, and meets the documented size limits."
        if path.suffix.casefold() == ".csv":
            return f"Imported {added} new CSV row(s) into searchable local knowledge from {path}. This does not train a model."
        return f"Imported {added} new text section(s) from {path}."

    def stats(self) -> str:
        return json.dumps({
            "memory_items": len(self.memory.recent(self.settings.max_memory_items)),
            "knowledge_items": self.knowledge.count,
            "auto_learning": self._auto_learn_enabled,
            "provider": self.provider.name if self.provider is not None else "offline",
            "built_in_tools": len(self.tools.list_tools()),
            "data_directory": str(self.settings.data_dir),
            "memory_directory": str(self.settings.memory_dir),
        }, indent=2)
