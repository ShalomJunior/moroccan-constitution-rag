import json
import tempfile
import unittest
from pathlib import Path
from constitution_evidence.experiments import compare_runs, oracle_context, run_oracle, select_validation
from constitution_evidence.store import write_jsonl


class ExperimentsTests(unittest.TestCase):
    def test_paired_run_comparison_and_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name, recall in [("left", 0.0), ("right", 1.0)]:
                run = base / name
                run.mkdir()
                manifest = {"split": "dev", "article_k": 10, "context_chars": 7000,
                            "question_ids": ["q1"], "question_count": 1,
                            "questions_sha256": "questions", "passages_sha256": "passages", "method": name}
                (run / "manifest.json").write_text(json.dumps(manifest))
                write_jsonl(run / "retrieval.jsonl", [{"question_id": "q1", "family_id": "f1",
                            "metrics": {"recall": recall, "mrr": recall, "complete_evidence": None}}])
            comparison = compare_runs(base / "left", base / "right")
            self.assertEqual(comparison["metrics"]["recall"]["mean_delta"], 1)
            manifest_path = base / "right" / "manifest.json"
            changed = json.loads(manifest_path.read_text())
            changed["questions_sha256"] = "different"
            manifest_path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                compare_runs(base / "left", base / "right")

    def test_selection_refuses_provisional_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            questions = base / "questions.jsonl"
            policy = base / "policy.json"
            write_jsonl(questions, [{"question_id": "q1", "family_id": "f1", "split": "validation",
                                     "review_status": "author_provisional", "acceptable_evidence_sets": [[{"passage_id": "p"}]]}])
            policy.write_text(json.dumps({"minimum_families": 1, "primary_metric": "complete_evidence", "tie_breaker": "mrr"}))
            with self.assertRaisesRegex(ValueError, "not all reviewed"):
                select_validation(questions, [base / "run"], policy)

    def test_oracle_uses_only_passages_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            passage = {"passage_id": "p1", "canonical_text": "La vie est protégée.", "text_hash": "hash",
                       "article_number": 20, "page_spans": [2]}
            passages = base / "passages.jsonl"
            questions = base / "questions.jsonl"
            write_jsonl(passages, [passage])
            question = {"question_id": "q1", "family_id": "f1", "split": "dev",
                        "question": "Quel droit ?", "review_status": "reviewed", "corpus_hash": "corpus",
                        "required_claims": ["secret answer label"],
                        "acceptable_evidence_sets": [[{"passage_id": "p1", "char_start": 0, "char_end": 2}]]}
            write_jsonl(questions, [question])
            self.assertEqual(oracle_context(question, [passage], "corpus"), [passage])
            class Model:
                model = "fake"
                calls = 0
                def generate(self, prompt, supplied, manifest):
                    self.calls += 1
                    assert "secret answer label" not in json.dumps(supplied)
                    return {"status": "insufficient_evidence", "claims": [], "sources": []}
            model = Model()
            manifest = {"corpus_hash": "corpus", "review_status": "reviewed"}
            first = run_oracle(questions, passages, manifest, base / "run", "dev", model)
            second = run_oracle(questions, passages, manifest, base / "run", "dev", model)
            self.assertEqual(first, second)
            self.assertEqual(model.calls, 1)
            with self.assertRaisesRegex(ValueError, "reviewed corpus"):
                run_oracle(questions, passages, {"corpus_hash": "corpus", "review_status": "unreviewed_ocr"},
                           base / "other", "dev", model)
            question["review_status"] = "author_provisional"
            with self.assertRaises(ValueError):
                oracle_context(question, [passage], "corpus")


if __name__ == "__main__":
    unittest.main()
