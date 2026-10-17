import unittest
from pathlib import Path
from unittest.mock import patch
from constitution_evidence.api import AskRequest, ask

class ApiContracts(unittest.TestCase):
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
        self.assertEqual(result["sources"][0]["article_number"], 1)

if __name__ == "__main__":
    unittest.main()
