import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from ruller_ai import RullerAI
from ruller_ai.adaptive_learning import AdaptiveLearning
from ruller_ai.config import Settings


class AdaptiveLearningTests(unittest.TestCase):
    def test_teaching_persists_updates_and_retrieves_relevant_examples(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "learning.json"
            learning = AdaptiveLearning(path)
            example_id = learning.teach("How do I reset local memory?", "Use the clear command; knowledge remains.")
            learning.teach("How do I reset local memory?", "Use /clear; it preserves knowledge.")
            restored = AdaptiveLearning(path)
            self.assertEqual(restored.example_count, 1)
            self.assertEqual(restored.matching_examples("reset local memory")[0]["id"], example_id)
            self.assertIn("preserves", restored.matching_examples("reset local memory")[0]["answer"])

    def test_feedback_requires_valid_rating_and_notes_are_retrievable(self):
        with tempfile.TemporaryDirectory() as temp:
            learning = AdaptiveLearning(Path(temp) / "learning.json")
            learning.record_feedback("Question", "Response", "not-helpful", "Be concise")
            self.assertEqual(learning.feedback_count, 1)
            self.assertEqual(learning.recent_notes(), ["Be concise"])
            with self.assertRaises(ValueError):
                learning.record_feedback("Question", "Response", "maybe")

    def test_engine_learning_commands_and_opt_in_legacy_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            ai = RullerAI(Settings(data_dir=Path(temp)))
            self.assertIn("Saved user-approved", ai.chat("/teach What is a widget? => A UI control."))
            self.assertIn("A UI control", ai.chat("What is a widget?"))
            self.assertIn("Feedback saved", ai.chat("/feedback helpful"))
            self.assertIn("approved examples: 1", ai.chat("/learning status"))
            ai.chat("/autolearn on")
            self.assertTrue(ai.learning.auto_learn_enabled)
            self.assertIn("Cleared", ai.chat("/learning forget all"))
            self.assertEqual(ai.learning.example_count, 0)
            self.assertTrue(ai.learning.auto_learn_enabled)

    def test_matching_examples_and_notes_are_added_to_model_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            ai = RullerAI(Settings(data_dir=Path(temp), provider="offline"))
            ai.learning.teach("How do I use safe mode?", "Use the supported setting.")
            ai.learning.record_feedback("How do I use safe mode?", "old answer", "not-helpful", "Mention safety constraints")
            mock_provider = Mock()
            mock_provider.name = "mock"
            mock_provider.generate.return_value = "answer"
            ai.provider = mock_provider
            self.assertEqual(ai._model_answer("How do I use safe mode?"), "answer")
            prompt = mock_provider.generate.call_args.args[0]
            self.assertIn("Use the supported setting", prompt)
            self.assertIn("Mention safety constraints", prompt)


if __name__ == "__main__":
    unittest.main()
