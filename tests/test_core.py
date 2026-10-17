import unittest
import tempfile
import json
from pathlib import Path
from constitution_evidence.ingestion import parse_articles, validate_articles, make_passages
from constitution_evidence.retrieval import BM25
from constitution_evidence.evidence import extractive_answer, validate_answer
from constitution_evidence.evaluation import score_retrieval, evaluate, report
from constitution_evidence.store import write_jsonl, read_jsonl

class Contracts(unittest.TestCase):
    def setUp(self):
        self.articles = parse_articles(["PRÉAMBULE\nTexte introductif\nArticle premier\nLa liberté de chaque citoyen est garantie par la Constitution.\nArticle 2\nLa justice de chaque citoyen est garantie par la Constitution."])
        self.passages = make_passages(self.articles)

    def test_article_boundary_and_inventory(self):
        self.assertEqual([a["article_number"] for a in self.articles], [0, 1, 2])
        validate_articles(self.articles, 2)
        with self.assertRaises(ValueError):
            validate_articles(self.articles, 3)

    def test_lookup_and_citation(self):
        hits = BM25(self.passages).search("article 2", 2)
        self.assertEqual(hits[0]["article_number"], 2)
        answer = extractive_answer(hits, {"source_url": "https://example.org/source.pdf"})
        self.assertEqual(answer["status"], "partially_answered")
        answer["claims"][0]["evidence_spans"][0]["quote"] = "invented"
        with self.assertRaises(ValueError):
            validate_answer(answer, hits)

    def test_article_dedup_and_cutoff(self):
        hits = [{"article_number": n} for n in [1] * 3 + list(range(2, 11)) + [11]]
        self.assertEqual(score_retrieval(hits, [11], 10)["mrr"], 0)

    def test_evidence_is_not_inferred_from_article_presence(self):
        span = {"passage_id": "a:p-2", "char_start": 0, "char_end": 4}
        hits = [{"article_number": 2, "passage_id": "a:p-1", "canonical_text": "irrelevant"},
                {"article_number": 2, "passage_id": "a:p-2", "canonical_text": "proof"}]
        article_only = score_retrieval(hits[:1], [2], 1)
        self.assertIsNone(article_only["complete_evidence"])
        missing = score_retrieval(hits[:1], [2], 1, [[span]], [span], hits[:1])
        self.assertEqual(missing["recall"], 1)
        self.assertEqual(missing["complete_evidence"], 0)
        covered = score_retrieval(hits, [2], 2, [[span]], [span], hits[:1])
        self.assertEqual(covered["complete_evidence"], 1)
        self.assertEqual(covered["span_recall"], 1)
        self.assertEqual(covered["context_evidence_coverage"], 0)

    def test_retrieval_run_resumes_and_rejects_changed_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            passage_path = base / "passages.jsonl"
            question_path = base / "questions.jsonl"
            run = base / "run"
            write_jsonl(passage_path, self.passages)
            questions = [{"question_id": str(i), "family_id": str(i), "split": "dev",
                          "question": "article 2", "relevant_articles": [2]} for i in range(2)]
            write_jsonl(question_path, questions)
            first = evaluate(question_path, passage_path, "dev", run, k=2)
            rows = read_jsonl(run / "retrieval.jsonl")
            write_jsonl(run / "retrieval.jsonl", rows[:1])
            self.assertEqual(evaluate(question_path, passage_path, "dev", run, k=2), first)
            self.assertEqual(len(read_jsonl(run / "retrieval.jsonl")), 2)
            with self.assertRaises(ValueError):
                evaluate(question_path, passage_path, "dev", run, k=1)

    def test_legacy_article_proxy_is_not_called_complete_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "manifest.json").write_text(json.dumps({"question_count": 1}))
            write_jsonl(run / "retrieval.jsonl", [{"question_id": "q1", "metrics": {
                "recall": 1.0, "mrr": 1.0, "complete_evidence": 1.0}}])
            summary = report(run)
            self.assertIsNone(summary["complete_evidence"])
            self.assertEqual(summary["legacy_article_coverage"], 1.0)

if __name__ == "__main__":
    unittest.main()
