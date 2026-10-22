import tempfile
import unittest
from pathlib import Path

from constitution_evidence.judgments import score_review_verdicts
from constitution_evidence.store import write_jsonl


class ReviewVerdictTests(unittest.TestCase):
    def test_scores_clean_and_acceptable_without_relabeling_minor_issues(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packets, mapping, reviews = [], [], []
            for family in ("f1", "f2"):
                for system in ("bm25_rag", "fulltext", "selected_pipeline"):
                    blind_id = f"{family}-{system}"
                    technical = family == "f2" and system == "fulltext"
                    packet = {"blind_id": blind_id, "question_id": family,
                              "family_id": family, "status": "technical_error" if technical else "answered",
                              "technical_error": technical}
                    packets.append(packet)
                    mapping.append({**packet, "system": system})
                    if not technical:
                        verdict = ("correct_minor_issues" if system == "bm25_rag" else
                                   "incorrect" if system == "selected_pipeline" else "correct")
                        reviews.append({**packet, "review": {
                            "verdict": verdict, "acceptable": verdict != "incorrect",
                            "quotes_verified_against_pdf": True, "citation_metadata_ok": True}})
            paths = [root / name for name in ("packets.jsonl", "mapping.jsonl", "reviewed.jsonl")]
            for path, rows in zip(paths, (packets, mapping, reviews)):
                write_jsonl(path, rows)
            result = score_review_verdicts(*paths, replications=100)
            self.assertEqual(result["systems"]["bm25_rag"]["clean_success_n"], 0)
            self.assertEqual(result["systems"]["bm25_rag"]["acceptable_n"], 2)
            self.assertEqual(result["systems"]["fulltext"]["technical_errors"], 1)
            self.assertEqual(result["systems"]["fulltext"]["clean_success_n"], 1)
            reviews[0]["review"]["acceptable"] = False
            write_jsonl(paths[2], reviews)
            with self.assertRaisesRegex(ValueError, "Verdict and acceptability disagree"):
                score_review_verdicts(*paths, replications=100)
            reviews[0]["review"]["acceptable"] = True
            reviews[0]["question_id"] = "changed"
            write_jsonl(paths[2], reviews)
            with self.assertRaisesRegex(ValueError, "differs from blind packet"):
                score_review_verdicts(*paths, replications=100)


if __name__ == "__main__":
    unittest.main()
