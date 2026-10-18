import tempfile
import unittest
from pathlib import Path

from constitution_evidence.question_audit import audit_questions
from constitution_evidence.store import write_jsonl


class QuestionAuditTests(unittest.TestCase):
    def test_rejects_reviewed_label_with_invalid_evidence_and_duplicate_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions, passages = root / "questions.jsonl", root / "passages.jsonl"
            write_jsonl(passages, [{"passage_id": "p1", "article_number": 20,
                                    "canonical_text": "La loi protège ce droit."}])
            row = {"question_id": "q1", "family_id": "f1", "split": "dev", "language": "fr",
                   "question": "Qui protège ce droit ?", "review_status": "reviewed", "corpus_hash": "hash",
                   "category": "direct", "theme": "droits", "expected_status": "answered",
                   "acceptable_statuses": ["answered"], "required_claims": ["La loi protège ce droit."],
                   "forbidden_inferences": [], "relevant_articles": [20],
                   "relevant_spans": [{"passage_id": "p1", "char_start": 0, "char_end": 99}],
                   "acceptable_evidence_sets": [[{"passage_id": "p1", "char_start": 0, "char_end": 99}]],
                   "annotator": "author", "source_edition": "2011-fr", "annotation_version": 1}
            write_jsonl(questions, [row, row])
            result = audit_questions(questions, passages, "hash")
            self.assertEqual(result["status"], "incomplete")
            self.assertIn("q1: duplicate question_id", result["problems"])
            self.assertIn("q1: evidence span is outside the current corpus", result["problems"])

    def test_provisional_questions_do_not_count_as_reviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions, passages = root / "questions.jsonl", root / "passages.jsonl"
            write_jsonl(questions, [{"question_id": "q1", "family_id": "f1", "split": "dev",
                                     "language": "fr", "question": "Que dit l'article 20 ?",
                                     "review_status": "author_provisional"}])
            result = audit_questions(questions, passages, "hash")
            self.assertEqual(result["reviewed_count"], 0)
            self.assertIn("q1: human annotation is not reviewed", result["problems"])

    def test_normalized_duplicate_question_cannot_cross_splits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions, passages = root / "questions.jsonl", root / "passages.jsonl"
            write_jsonl(questions, [
                {"question_id": "d1", "family_id": "d1", "split": "dev", "language": "fr",
                 "question": "Quel est le délai prévu ?", "review_status": "author_provisional"},
                {"question_id": "v1", "family_id": "v1", "split": "validation", "language": "fr",
                 "question": "QUEL est le delai prévu!", "review_status": "author_provisional"}])
            result = audit_questions(questions, passages, "hash")
            self.assertIn("v1: exact question wording crosses splits with d1", result["problems"])


if __name__ == "__main__":
    unittest.main()
