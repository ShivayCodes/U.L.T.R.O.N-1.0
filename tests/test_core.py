import logging
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from ruller_ai import RullerAI
from ruller_ai.config import Settings
from ruller_ai.knowledge import KnowledgeBase
from ruller_ai.memory import MemoryStore
from ruller_ai.reasoning import UnsafeExpression, safe_calculate
from ruller_ai.tools import Permission, ToolError, ToolRegistry, ToolSpec, create_builtin_registry


class RullerAITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ai = RullerAI(Settings(data_dir=Path(self.temp.name)))

    def tearDown(self):
        self.temp.cleanup()

    def test_calculator(self):
        self.assertEqual(safe_calculate("2 + 3 * 4"), 14)
        self.assertEqual(safe_calculate("(10 - 4) / 2"), 3)

    def test_rejects_code_execution(self):
        for expression in ("__import__('os').system('echo unsafe')", "2 ** 999", "open('secret')"):
            with self.subTest(expression=expression):
                with self.assertRaises(UnsafeExpression):
                    safe_calculate(expression)

    def test_help_and_greeting(self):
        self.assertIn("ULTRON commands", self.ai.chat("/help"))
        self.assertIn("Hello", self.ai.chat("hello"))

    def test_learn_and_retrieve(self):
        self.ai.chat("/learn Python is a programming language used for automation.")
        result = self.ai.chat("/search Python automation")
        self.assertIn("programming language", result)

    def test_memory_persists(self):
        self.ai.chat("/remember test note")
        again = RullerAI(Settings(data_dir=Path(self.temp.name)))
        self.assertTrue(any("test note" in item["content"] for item in again.memory.recent(10)))

    def test_auto_learns_and_preserves_memory(self):
        self.ai.chat("I like to use Python for automation and testing.")
        again = RullerAI(Settings(data_dir=Path(self.temp.name)))
        self.assertTrue(any("Python" in item["content"] for item in again.memory.recent(20)))

    def test_memory_guard_rejects_external_tampering(self):
        guard = Path(self.temp.name) / "memory" / ".memory_guard.json"
        self.ai.chat("/remember test note")
        with open(guard, "w", encoding="utf-8") as handle:
            handle.write('{"tampered": true}')
        with self.assertRaises(RuntimeError):
            RullerAI(Settings(data_dir=Path(self.temp.name)))

    def test_empty_input(self):
        self.assertEqual(self.ai.chat("   "), "Please enter a message.")

    def test_ingest_rejects_unknown_extension(self):
        path = Path(self.temp.name) / "file.exe"
        path.write_text("not allowed", encoding="utf-8")
        result = self.ai.chat(f"/ingest {path}")
        self.assertIn("Unsupported file type", result)

    def test_knowledge_index_deduplicates_and_tracks_eviction(self):
        path = Path(self.temp.name) / "indexed-knowledge.json"
        knowledge = KnowledgeBase(path, max_items=2)
        self.assertTrue(knowledge.add_text("alpha beta"))
        self.assertFalse(knowledge.add_text("alpha beta"))
        knowledge.add_text("beta gamma")
        knowledge.add_text("gamma delta")
        self.assertEqual(knowledge.count, 2)
        self.assertEqual([item["text"] for item in knowledge.search("alpha")], [])
        self.assertEqual([item["text"] for item in knowledge.search("gamma")], ["beta gamma", "gamma delta"])
        self.assertTrue(knowledge.add_text("alpha beta"))

    def test_memory_index_tracks_append_eviction_and_clear(self):
        path = Path(self.temp.name) / "indexed-memory.json"
        memory = MemoryStore(path, max_items=2, guard_path=Path(self.temp.name) / "indexed-guard.json")
        memory.add("user", "alpha beta")
        memory.add("user", "beta gamma")
        memory.add("user", "gamma delta")
        self.assertEqual([item["content"] for item in memory.search("alpha")], [])
        self.assertEqual([item["content"] for item in memory.search("gamma")], ["beta gamma", "gamma delta"])
        memory.clear()
        self.assertEqual(memory.search("gamma"), [])

    def test_builtin_tools_are_listed_and_safe(self):
        registry = create_builtin_registry()
        self.assertEqual([tool.permission for tool in registry.list_tools()], [Permission.SAFE] * 3)
        self.assertEqual(self.ai.chat("/tool list").count("[SAFE]"), 3)
        self.assertIn("No arbitrary shell or Python", self.ai.chat("/tool status"))
        self.assertIn("local system time", self.ai.chat("/time"))

    def test_unit_conversion(self):
        self.assertEqual(self.ai.chat("/convert 10 km to miles"), "10 km = 6.213711922373339795 miles")
        self.assertEqual(self.ai.chat("/convert 0 c to f"), "0 c = 32 f")
        self.assertIn("same category", self.ai.chat("/convert 1 km to kg"))
        self.assertIn("Usage:", self.ai.chat("/convert 10 km"))

    def test_relative_date_tool(self):
        self.assertEqual(self.ai.chat("/date today"), f"{date.today().isoformat()} ({date.today().strftime('%A')})")
        expected = date.today() + timedelta(days=7)
        self.assertEqual(self.ai.chat("/date in 1 week"), f"{expected.isoformat()} ({expected.strftime('%A')})")
        self.assertIn("Usage:", self.ai.chat("/date next month"))

    def test_registry_requires_confirmation_and_audits_without_arguments(self):
        registry = ToolRegistry()
        registry.register(ToolSpec("write", "test", Permission.CONFIRM, "text", "writes", lambda arg: "done"))
        with self.assertLogs("ruller_ai.tools", level="INFO") as captured:
            with self.assertRaises(ToolError):
                registry.run("write", "sensitive-secret")
        self.assertIn("confirmation_required", captured.output[0])
        self.assertNotIn("sensitive-secret", captured.output[0])
        self.assertEqual(registry.run("write", "safe", confirmed=True), "done")

    def test_tool_input_is_bounded_and_unknown_tools_rejected(self):
        registry = create_builtin_registry()
        with self.assertRaises(ToolError):
            registry.run("convert", "x" * 301)
        with self.assertRaises(ToolError):
            registry.run("shell", "anything")


if __name__ == "__main__":
    unittest.main()
