import unittest

from tools.import_wikiwhy import _column_values, format_ultron_passage


class WikiWhyImporterTests(unittest.TestCase):
    def test_formats_answer_fields_before_bounded_context(self):
        context = "background " * 500
        passage = format_ultron_passage({
            "question": "Why did the event occur?",
            "cause": "A preceding event",
            "effect": "The resulting event",
            "explanation": "The cause led to the effect.",
            "topic": "History",
            "title": "Example article",
            "ctx": context,
        })

        self.assertLess(passage.index("Question:"), passage.index("Cause:"))
        self.assertLess(passage.index("Cause:"), passage.index("Explanation:"))
        self.assertLess(passage.index("Explanation:"), passage.index("Context excerpt:"))
        self.assertIn("The cause led to the effect.", passage)
        self.assertLess(len(passage), 15_000)

    def test_normalizes_column_oriented_dataset_json(self):
        columns = _column_values(
            {"question": {"0": "Why?", "1": "How?"}},
            ("question", "cause"),
            "question.json",
        )
        self.assertEqual(columns["question"], ["Why?", "How?"])
        self.assertEqual(columns["cause"], [])

    def test_normalizes_record_oriented_dataset_json(self):
        columns = _column_values(
            [{"question": "Why?", "cause": "Because"}],
            ("question", "cause"),
            "records.json",
        )
        self.assertEqual(columns, {"question": ["Why?"], "cause": ["Because"]})


if __name__ == "__main__":
    unittest.main()
