"""Orchestrates local memory, knowledge retrieval, web lookup, and responses."""
import json
from datetime import datetime
from pathlib import Path

from .config import Settings
from .knowledge import KnowledgeBase
from .memory import MemoryStore
from .reasoning import UnsafeExpression, safe_calculate
from .storage import read_json, write_json
from .web_search import search_web


class RullerAI:
    """Offline-first assistant; network lookup is explicit and opt-in per query."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory = MemoryStore(
            self.settings.memory_file,
            self.settings.max_memory_items,
            self.settings.guard_file,
        )
        self.knowledge = KnowledgeBase(self.settings.knowledge_file, self.settings.max_knowledge_items)
        self.learning_file = self.settings.data_dir / "learning.json"
        learning = read_json(self.learning_file, {})
        self._auto_learn_enabled = isinstance(learning, dict) and learning.get("enabled") is True

    def chat(self, message: str) -> str:
        text = message.strip()
        if not text:
            return "Please enter a message."
        if len(text) > self.settings.max_input_chars:
            return f"Your message is too long. Limit: {self.settings.max_input_chars} characters."

        self.memory.add("user", text)
        lowered = text.casefold()

        if lowered in {"/help", "help"}:
            answer = self.help_text()
        elif lowered in {"/time", "what time is it", "what is the time"}:
            answer = datetime.now().astimezone().strftime("Your local system time is %Y-%m-%d %H:%M:%S %Z.")
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
            answer = self._web_lookup(text[len("/research "):].strip(), save=True)
        elif lowered in {"/stats", "stats"}:
            answer = self.stats()
        elif lowered in {"hi", "hello", "hey", "hello ruller", "hi ruller"}:
            answer = "Hello! I'm Ruller AI, your local assistant prototype. Ask a question, use /help, or teach me with /learn."
        else:
            answer = self._answer_from_knowledge(text)
            if self._auto_learn_enabled and not text.startswith("/"):
                self.knowledge.add_text(text, "opt-in conversation learning")

        self.memory.add("assistant", answer)
        return answer

    @staticmethod
    def help_text() -> str:
        return (
            "Ruller AI commands:\n"
            "  /help                 Show this help\n"
            "  /calc 12 * (3 + 2)    Safely calculate arithmetic\n"
            "  /learn some fact      Add text to local knowledge\n"
            "  /search keywords      Search local knowledge\n"
            "  /ingest path          Import a supported local text file (max 1 MB)\n"
            "  /remember a note      Save a note to conversation memory\n"
            "  /autolearn on|off     Opt in/out of saving future chat messages to knowledge\n"
            "  /web query            Search the web without saving results\n"
            "  /research query       Search the web and save returned snippets locally\n"
            "  /stats                Show local data counts\n"
            "  /time                 Show local system time\n"
            "  /clear                Clear conversation memory only\n"
            "Web results are external and may be incomplete or inaccurate."
        )

    def _autolearn(self, option: str) -> str:
        if option.casefold() == "status":
            state = "on" if self._auto_learn_enabled else "off"
            return f"Opt-in conversation learning is {state}."
        if option.casefold() not in {"on", "off"}:
            return "Usage: /autolearn on | /autolearn off | /autolearn status"
        self._auto_learn_enabled = option.casefold() == "on"
        write_json(self.learning_file, {"enabled": self._auto_learn_enabled})
        if self._auto_learn_enabled:
            return "Opt-in learning enabled. Future ordinary messages may be saved to the local knowledge base; existing history is unchanged."
        return "Opt-in learning disabled. Existing memory and knowledge were not deleted."

    def _web_lookup(self, query: str, *, save: bool) -> str:
        if not query:
            command = "/research" if save else "/web"
            return f"Usage: {command} search terms"
        try:
            results = search_web(query, limit=5)
        except (OSError, RuntimeError, ValueError) as exc:
            return f"Web lookup failed: {exc}"
        if not results:
            return "No web results were returned. Try a different query or use /search for local knowledge."

        lines = []
        for index, result in enumerate(results, 1):
            title = result["title"]
            url = result["url"]
            snippet = result["snippet"]
            lines.append(f"{index}. {title}\n   {snippet}\n   Source: {url}")
            if save:
                retrieved = datetime.now().astimezone().isoformat(timespec="seconds")
                self.knowledge.add_text(
                    f"{title}\n{snippet}\nRetrieved: {retrieved}",
                    url,
                )
        heading = "Web results saved to local knowledge (verify sources and dates):\n" if save else "Web results (not saved):\n"
        return heading + "\n".join(lines)

    def _calculate(self, expression: str) -> str:
        try:
            return f"{expression.strip()} = {safe_calculate(expression)}"
        except UnsafeExpression as exc:
            return f"Calculation rejected: {exc}"

    def _remember(self, note: str) -> str:
        self.memory.add("system", "User note: " + note)
        return "Saved that note in local memory."

    def _search(self, query: str) -> str:
        results = self.knowledge.search(query, limit=5)
        if not results:
            return "No matching local knowledge found. Add information with /learn, /ingest, or /research."
        return "\n".join(
            f"{index}. [{item['score']:.3f}] {item['text']} (source: {item['source']})"
            for index, item in enumerate(results, 1)
        )

    def _answer_from_knowledge(self, query: str) -> str:
        results = self.knowledge.search(query, limit=3)
        if results:
            best = results[0]
            return (
                "I found a potentially relevant passage in your local knowledge base "
                f"(lexical match score {best['score']:.3f}):\n\n{best['text']}\n\n"
                f"Source: {best['source']}\n"
                "This is retrieval, not proof that the passage is correct. Use /search for more matches."
            )
        prior = self.memory.search(query, limit=2)
        if prior:
            excerpt = prior[0].get("content", "")
            return (
                "I don't have a general-purpose language model connected, and found no matching knowledge. "
                f"A related prior conversation entry was: {excerpt}\n\n"
                "Use /web to look up current sources, or add trusted information with /learn or /ingest."
            )
        return (
            "I'm running in offline baseline mode, so I can't reliably answer open-ended questions yet. "
            "Use /web for an explicit web lookup, /learn to add trusted material, or /ingest to import a text file."
        )

    def _ingest(self, raw_path: str) -> str:
        value = raw_path.strip().strip('"')
        if not value:
            return "Usage: /ingest path/to/file.txt"
        path = Path(value).expanduser()
        try:
            added = self.knowledge.ingest_file(path)
        except (OSError, ValueError, RuntimeError) as exc:
            return f"Import failed: {exc}"
        return f"Imported {added} new text section(s) from {path}."

    def stats(self) -> str:
        return json.dumps(
            {
                "memory_items": len(self.memory.recent(limit=self.settings.max_memory_items)),
                "knowledge_items": self.knowledge.count,
                "auto_learning": self._auto_learn_enabled,
                "data_directory": str(self.settings.data_dir),
                "memory_directory": str(self.settings.memory_dir),
            },
            indent=2,
        )
