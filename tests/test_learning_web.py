import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ruller_ai import RullerAI
from ruller_ai.config import Settings
from ruller_ai.knowledge import KnowledgeBase
from ruller_ai.web_search import parse_search_results


class LearningAndWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name)
        self.ai = RullerAI(Settings(data_dir=self.data_dir))

    def tearDown(self):
        self.temp.cleanup()

    def test_auto_learning_is_opt_in_and_persists(self):
        self.ai.chat("A sufficiently long sentence to check learning behavior.")
        self.assertEqual(self.ai.knowledge.count, 0)
        self.ai.chat("/autolearn on")
        self.ai.chat("A second sufficiently long sentence for local learning.")
        self.assertGreater(self.ai.knowledge.count, 0)
        restored = RullerAI(Settings(data_dir=self.data_dir))
        self.assertIn("on", restored.chat("/autolearn status"))
        restored.chat("/autolearn off")
        before = restored.knowledge.count
        restored.chat("A third sufficiently long sentence without auto learning.")
        self.assertEqual(restored.knowledge.count, before)

    def test_csv_ingestion_indexes_rows_and_survives_restart(self):
        dataset = self.data_dir / "facts.csv"
        dataset.write_text(
            "topic,detail\nPython,Supports readable automation\nMemory,Stores searchable passages\n",
            encoding="utf-8",
        )

        response = self.ai.chat(f"/ingest {dataset}")

        self.assertIn("Imported 2 new CSV row(s)", response)
        self.assertIn("does not train a model", response)
        result = self.ai.knowledge.search("Python automation", limit=1)[0]
        self.assertIn("topic: Python", result["text"])
        self.assertIn("detail: Supports readable automation", result["text"])
        restored = RullerAI(Settings(data_dir=self.data_dir))
        self.assertEqual(restored.knowledge.search("Memory passages", limit=1)[0]["source"], str(dataset))

    def test_csv_ingestion_rejects_files_over_limit(self):
        dataset = self.data_dir / "large.csv"
        dataset.write_text("x\n", encoding="utf-8")
        with patch.object(KnowledgeBase, "MAX_CSV_BYTES", 1):
            response = self.ai.chat(f"/ingest {dataset}")
        self.assertIn("larger than 200 MB", response)
        self.assertEqual(self.ai.knowledge.count, 0)

    def test_malformed_csv_does_not_partially_add_rows(self):
        dataset = self.data_dir / "malformed.csv"
        dataset.write_text('topic,detail\nfirst,valid\nsecond,"unterminated\n', encoding="utf-8")

        response = self.ai.chat(f"/ingest {dataset}")

        self.assertIn("Malformed CSV dataset", response)
        self.assertEqual(self.ai.knowledge.count, 0)
        self.assertEqual(self.ai.knowledge.search("valid", limit=1), [])

    @patch("ruller_ai.engine.search_web")
    def test_web_lookup_does_not_save_unless_research_requested(self, mock_search):
        mock_search.return_value = [{
            "title": "Example result",
            "url": "https://example.com/article",
            "snippet": "A short source excerpt.",
        }]
        answer = self.ai.chat("/web latest topic")
        self.assertIn("not saved", answer)
        self.assertEqual(self.ai.knowledge.count, 0)

        answer = self.ai.chat("/research latest topic")
        self.assertIn("saved to local knowledge", answer)
        self.assertEqual(self.ai.knowledge.count, 1)
        self.assertEqual(self.ai.knowledge.search("Example result", limit=1)[0]["source"], "https://example.com/article")

    def test_parser_extracts_result_title_url_and_snippet(self):
        html = (
            '<a class="result__a" href="https://example.com">Example title</a>'
            '<a class="result__snippet">Useful <b>source</b> snippet</a>'
        )
        results = parse_search_results(html)
        self.assertEqual(results, [{
            "title": "Example title",
            "url": "https://example.com",
            "snippet": "Useful source snippet",
        }])


if __name__ == "__main__":
    unittest.main()
