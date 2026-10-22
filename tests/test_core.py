import unittest
import tempfile
import json
from pathlib import Path
from constitution_evidence.ingestion import parse_articles, validate_articles, make_passages
from unittest.mock import patch
from constitution_evidence.retrieval import BM25, Hybrid, explicit_article_numbers
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

    def test_multiple_explicit_articles_get_distinct_first_passages(self):
        self.assertEqual(explicit_article_numbers("Comparer les articles 20, 21 et 22"), [20, 21, 22])
        self.assertEqual(explicit_article_numbers("article 1 et article 2"), [1, 2])
        hits = BM25(self.passages).search("Comparer les articles 1 et 2", 2)
        self.assertEqual([hit["article_number"] for hit in hits], [1, 2])
        self.assertTrue(all(hit["retriever"] == "article_lookup" for hit in hits))
        preamble = BM25(self.passages).search("Que dit le préambule ?", 1)
        self.assertEqual(preamble[0]["article_number"], 0)

    def test_hybrid_explicit_lookup_does_not_load_dense_model(self):
        with patch("constitution_evidence.retrieval.Dense", side_effect=AssertionError("dense loaded")):
            hits = Hybrid(self.passages).search("articles 1 et 2", 2)
        self.assertEqual([hit["article_number"] for hit in hits], [1, 2])

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

    def test_out_of_scope_label_has_no_complete_evidence_score(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            passages, questions, run = base / "passages.jsonl", base / "questions.jsonl", base / "run"
            write_jsonl(passages, self.passages)
            write_jsonl(questions, [{"question_id": "q1", "family_id": "q1", "split": "validation",
                                     "question": "Quel montant exact ?", "expected_status": "out_of_scope",
                                     "relevant_articles": [2], "relevant_spans": [{"passage_id": self.passages[-1]["passage_id"],
                                     "char_start": 0, "char_end": 10}], "acceptable_evidence_sets": []}])
            result = evaluate(questions, passages, "validation", run, k=2)
            self.assertIsNone(result["complete_evidence"])

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
