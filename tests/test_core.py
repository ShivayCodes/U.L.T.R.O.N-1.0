import tempfile
import unittest
from pathlib import Path

from ruller_ai import RullerAI
from ruller_ai.config import Settings
from ruller_ai.reasoning import UnsafeExpression, safe_calculate


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
        self.assertIn("Ruller AI commands", self.ai.chat("/help"))
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