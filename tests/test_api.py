import unittest
from pathlib import Path
from unittest.mock import patch
from constitution_evidence.api import AskRequest, ask, capabilities, version

class ApiContracts(unittest.TestCase):
    def test_local_capability_is_false_when_server_is_absent(self):
        with patch("constitution_evidence.api.urlopen", side_effect=OSError("connection refused")):
            self.assertFalse(capabilities()["local_generation_available"])

    def test_retrieval_strategy_is_passed_to_engine_and_returned(self):
        fake = {"passage_id": "p-1", "article_number": 1, "canonical_text": "Une preuve.",
                "text_hash": "hash", "page_spans": [3], "score": 1.0}
        class Engine:
            def search(self, question, top_k):
                self.called = (question, top_k)
                return [fake]
        engine = Engine()
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_corpus", return_value=(None, {"source_url": "https://example.org/a.pdf"}, {})):
                with patch("constitution_evidence.api._engine", return_value=engine) as select:
                    result = ask(AskRequest(question="article 1", top_k=3, strategy="hybrid"))
        self.assertEqual(engine.called, ("article 1", 3))
        self.assertEqual(select.call_args.args[1], "hybrid")
        self.assertEqual(result["retrieval_strategy"], "hybrid")
        self.assertEqual(result["retrieved_passage_count"], 1)
        self.assertEqual(result["sources"][0]["article_number"], 1)

    def test_reference_expansion_selects_bounded_engine(self):
        class Engine:
            def search(self, question, top_k):
                return []
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_corpus", return_value=(None, {"source_url": "https://example.org/a.pdf"}, {})):
                with patch("constitution_evidence.api._reference_engine", return_value=Engine()) as select:
                    result = ask(AskRequest(question="article 1", expand_references=True))
        self.assertEqual(select.call_args.args[1], "bm25")
        self.assertTrue(result["reference_expansion"])

    def test_decomposition_trace_reports_supplied_context(self):
        passage = {"passage_id": "p-1", "article_number": 1, "canonical_text": "Une preuve.",
                   "text_hash": "hash", "page_spans": [3]}
        trace = {"subquestions": ["article 1"], "retrieval_calls": 2}
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_corpus", return_value=(None, {"source_url": "https://example.org/a.pdf"}, {})):
                with patch("constitution_evidence.api._engine", return_value=object()):
                    with patch("constitution_evidence.decomposition.retrieve_multi", return_value=([passage], trace)):
                        result = ask(AskRequest(question="Question ?", decompose=True))
        self.assertEqual(result["decomposition"]["context_passage_ids"], ["p-1"])

    def test_retrieved_passages_remain_visible_when_groq_abstains(self):
        hit = {"passage_id": "p-20", "article_number": 20, "paragraph_index": 1,
               "canonical_text": "Le droit à la vie est le droit premier.",
               "text_hash": "hash", "page_spans": [7], "retriever": "bm25s"}
        class Engine:
            def search(self, question, top_k):
                return [hit]
        manifest = {"source_url": "https://example.org/constitution.pdf", "review_status": "reviewed"}
        answer = {"status": "insufficient_evidence", "claims": [], "sources": [], "limitations": "Preuve insuffisante."}
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_corpus", return_value=(None, manifest, {"p-20": hit})):
                with patch("constitution_evidence.api._engine", return_value=Engine()):
                    with patch("constitution_evidence.groq_generation.GroqGenerator") as generator:
                        generator.return_value.generate.return_value = answer
                        result = ask(AskRequest(question="Question ?", generator="groq"))
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["retrieved_passage_count"], 1)
        self.assertEqual(result["retrieved_passages"][0]["passage_id"], "p-20")
        self.assertTrue(result["retrieved_passages"][0]["included_in_context"])
        self.assertEqual(result["retrieved_passages"][0]["page_spans"], [7])
        self.assertEqual(result["review_status"], "reviewed")

    def test_version_exposes_actual_review_status(self):
        with patch("constitution_evidence.api.corpus", return_value=(None, {"corpus_hash": "abc",
                "edition_id": "2011-fr", "review_status": "reviewed"}, {})):
            self.assertEqual(version()["review_status"], "reviewed")

if __name__ == "__main__":
    unittest.main()
