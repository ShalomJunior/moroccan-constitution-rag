import tempfile
import unittest
from pathlib import Path

from constitution_evidence.question_spans import locate_span
from constitution_evidence.store import digest, write_jsonl


class QuestionSpanTests(unittest.TestCase):
    def test_exact_unique_quote_and_changed_corpus_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            passages = Path(directory) / "passages.jsonl"
            write_jsonl(passages, [{"passage_id": "p1", "article_number": 20,
                                    "canonical_text": "La loi protège ce droit.", "text_hash": "text-hash"}])
            manifest = {"review_status": "reviewed", "passages_hash": digest(passages.read_bytes())}
            span = locate_span(passages, manifest, "p1", "protège ce droit")
            self.assertEqual((span["char_start"], span["char_end"]), (7, 23))
            with self.assertRaisesRegex(ValueError, "exact substring"):
                locate_span(passages, manifest, "p1", "protège ses droits")
            passages.write_text(passages.read_text().replace("protège", "ignore"))
            with self.assertRaisesRegex(ValueError, "active reviewed corpus"):
                locate_span(passages, manifest, "p1", "La loi")

    def test_repeated_quote_needs_longer_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            passages = Path(directory) / "passages.jsonl"
            write_jsonl(passages, [{"passage_id": "p1", "article_number": 20,
                                    "canonical_text": "la loi et la loi", "text_hash": "text-hash"}])
            manifest = {"review_status": "reviewed", "passages_hash": digest(passages.read_bytes())}
            with self.assertRaisesRegex(ValueError, "more than once"):
                locate_span(passages, manifest, "p1", "la loi")


if __name__ == "__main__":
    unittest.main()
