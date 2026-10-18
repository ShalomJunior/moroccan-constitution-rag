import json
import tempfile
import unittest
from pathlib import Path

from constitution_evidence.groq_calibration import run_calibration
from constitution_evidence.store import digest, write_jsonl


class CalibrationContracts(unittest.TestCase):
    def test_completed_run_resumes_without_second_provider_call(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            question_path, passage_path, manifest_path = (root / name for name in ("questions.jsonl", "passages.jsonl", "manifest.json"))
            write_jsonl(question_path, [{"question_id": "q1", "split": "dev", "question": "Que dit l'article 20 ?"}])
            write_jsonl(passage_path, [{"passage_id": "p1", "article_number": 20,
                                        "paragraph_index": 1, "canonical_text": "Le droit à la vie est protégé.", "text_hash": "hash",
                                        "page_spans": [7]}])
            manifest_path.write_text(json.dumps({"corpus_hash": "corpus", "passages_hash": digest(passage_path.read_bytes()),
                                                 "review_status": "unreviewed_ocr", "source_url": "https://example.org/a.pdf"}))
            class FakeGenerator:
                model = "openai/gpt-oss-20b"
                calls = 0
                def generate(self, question, context, manifest):
                    self.calls += 1
                    return {"status": "partially_answered", "claims": [], "usage": {"total_tokens": 4}}
            model = FakeGenerator()
            first = run_calibration(question_path, passage_path, manifest_path, root / "run", model, pause_seconds=0)
            second = run_calibration(question_path, passage_path, manifest_path, root / "run", model, pause_seconds=0)
            self.assertEqual(model.calls, 1)
            self.assertEqual(first, second)
            self.assertEqual(first["token_totals"]["total_tokens"], 4)


if __name__ == "__main__":
    unittest.main()
