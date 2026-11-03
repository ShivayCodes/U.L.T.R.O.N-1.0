"""Orchestrates local memory, knowledge retrieval, and transparent responses."""
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .knowledge import KnowledgeBase
from .memory import MemoryStore
from .reasoning import UnsafeExpression, safe_calculate


class RullerAI:
    """Offline-first assistant baseline; it does not pretend to be a trained LLM."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings o                  r Settings()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory = MemoryStore(
            self.settings.memory_file,
            self.settings.max_memory_items,
            self.settings.guard_file,
        )
        self.knowledge = KnowledgeBase(self.settings.knowledge_file, self.settings.max_knowledge_items)

    def _learn_from_conversation(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        if len(cleaned) < 8:
            return
        self.memory.add_auto_memory("conversation", cleaned)

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
            answer = "Conversation memory cleared."
        elif lowered.startswith("/calc "):
            answer = self._calculate(text[6:])
        elif lowered.startswith("/remember "):
            fact = text[len("/remember ") :].strip()
            answer = "Tell me what to remember after /remember." if not fact else self._remember(fact)
        elif lowered.startswith("/learn "):
            fact = text[len("/learn ") :].strip()
            if fact:
                added = self.knowledge.add_text(fact, "user note")
                self.memory.add_auto_memory("learn-command", fact)
                answer = "Saved to the local knowledge base and protected memory." if added else "That note is already in the knowledge base."
            else:
                answer = "Usage: /learn text you want to add"
        elif lowered.startswith("/search "):
            answer = self._search(text[8:])
        elif lowered.startswith("/ingest "):
            answer = self._ingest(text[8:])
        elif lowered in {"/stats", "stats"}:
            answer = self.stats()
        elif lowered in {"hi", "hello", "hey", "hello ruller", "hi ruller"}:
            answer = "Hello! I'm Ruller AI, your local assistant prototype. Ask a question, use /help, or teach me with /learn."
        else:
            answer = self._answer_from_knowledge(text)
            self._learn_from_conversation(text)

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
            "  /stats                Show local data counts\n"
            "  /time                 Show local system time\n"
            "  /clear                Clear conversation memory\n"
            "Memory is stored in ~/.ruller_ai/memory and protected with a tamper-detection guard."
        )

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
            return "No matching local knowledge found. Add information with /learn or /ingest."
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
                "Add trusted information with /learn or /ingest, or connect a model in a future extension."
            )
        return (
            "I'm running in offline baseline mode, so I can't reliably answer open-ended questions yet. "
            "You can use /help, calculate with /calc, add trusted material with /learn, "
            "import a text file with /ingest, and search it with /search. "
            "This system keeps memory in a protected local folder for reuse."
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
                "data_directory": str(self.settings.data_dir),
                "memory_directory": str(self.settings.memory_dir),
            },
            indent=2,
        )