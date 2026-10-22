import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from constitution_evidence.evaluation import evaluate
from constitution_evidence.reproduction import reproduce_retrieval, publication_audit
from constitution_evidence.store import write_jsonl, read_jsonl


class ReproductionTests(unittest.TestCase):
    def test_saved_metrics_recompute_and_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions, passages, run = root / "questions.jsonl", root / "passages.jsonl", root / "run"
            write_jsonl(questions, [{"question_id": "q1", "family_id": "f1", "split": "dev",
                                     "question": "article 20", "relevant_articles": [20]}])
            write_jsonl(passages, [{"passage_id": "p1", "article_number": 20, "paragraph_index": 1,
                                    "canonical_text": "Le droit à la vie est protégé.", "text_hash": "hash"}])
            evaluate(questions, passages, "dev", run, k=1)
            result = reproduce_retrieval(questions, passages, [run])
            self.assertEqual(result["runs"]["run"]["recall"], 1)
            rows = read_jsonl(run / "retrieval.jsonl")
            rows[0]["metrics"]["recall"] = 0
            write_jsonl(run / "retrieval.jsonl", rows)
            with self.assertRaisesRegex(ValueError, "do not match"):
                reproduce_retrieval(questions, passages, [run])

    def test_unanswerable_question_with_empty_evidence_reproduces(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions, passages, run = root / "questions.jsonl", root / "passages.jsonl", root / "run"
            write_jsonl(questions, [{"question_id": "q1", "family_id": "f1", "split": "validation",
                                     "question": "Quel est le taux actuel ?", "relevant_articles": [],
                                     "acceptable_evidence_sets": [], "relevant_spans": []}])
            write_jsonl(passages, [{"passage_id": "p1", "article_number": 20, "paragraph_index": 1,
                                    "canonical_text": "Le droit à la vie.", "text_hash": "hash"}])
            evaluate(questions, passages, "validation", run, k=1)
            result = reproduce_retrieval(questions, passages, [run])
            self.assertEqual(result["runs"]["run"]["questions"], 1)

    def test_publication_audit_flags_tracked_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("GEMINI_API_KEY=not-a-real-key")
            with patch("constitution_evidence.reproduction.subprocess.check_output", return_value=b".env\0"):
                result = publication_audit(root)
            self.assertEqual(result["status"], "review_required")
            self.assertEqual(result["findings"][0]["path"], ".env")

    def test_publication_audit_flags_reserved_test_drafts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "data/annotations/test-candidates.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text('{}\n')
            with patch("constitution_evidence.reproduction.subprocess.check_output",
                       return_value=b"data/annotations/test-candidates.jsonl\0"):
                result = publication_audit(root)
            self.assertEqual(result["status"], "review_required")
            self.assertEqual(result["findings"][0]["path"], "data/annotations/test-candidates.jsonl")


if __name__ == "__main__":
    unittest.main()
