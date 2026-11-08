import csv
import tempfile
import unittest
from pathlib import Path

from ruller_ai.knowledge import KnowledgeBase


class CsvErrorClassificationTests(unittest.TestCase):
    def test_invalid_utf8_has_encoding_diagnosis_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = KnowledgeBase(root / "knowledge.json")
            db.add_text("existing material", "test")
            csv_path = root / "invalid.csv"
            csv_path.write_bytes(b"column\n\\xff\n")
            with self.assertRaisesRegex(ValueError, "valid UTF-8"):
                db.ingest_csv(csv_path)
            self.assertEqual(db.count, 1)
            self.assertEqual(len(db.search("existing")), 1)

    def test_malformed_csv_is_not_mislabeled_as_encoding_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.csv"
            path.write_text('a\n"unterminated\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Malformed CSV"):
                KnowledgeBase(Path(temp) / "knowledge.json").ingest_csv(path)

    def test_csv_field_limit_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "large-field.csv"
            path.write_text("value\n" + "x" * (KnowledgeBase.MAX_CSV_FIELD_CHARS + 1) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "field exceeds"):
                KnowledgeBase(root / "knowledge.json").ingest_csv(path)


if __name__ == "__main__":
    unittest.main()
