import io
import json
import unittest
from unittest.mock import patch
from constitution_evidence.decomposition import LocalDecomposer, explicit_plan, retrieve_multi
from constitution_evidence.generation import GenerationError

class DecompositionContracts(unittest.TestCase):
    def test_explicit_articles_use_at_most_three_retrieval_calls_without_model(self):
        self.assertEqual(explicit_plan("Comparer les articles 20 et 21"), ["article 20", "article 21"])
        class Engine:
            calls = []
            def search(self, question, k):
                self.calls.append((question, k))
                number = 21 if question.startswith("article 21") else 20
                return [{"passage_id": f"p-{number}", "article_number": number,
                         "canonical_text": f"Article {number}", "score": 1.0, "rank": 1}]
        engine = Engine()
        with patch("constitution_evidence.decomposition.LocalDecomposer", side_effect=AssertionError("model called")):
            hits, trace = retrieve_multi("Comparer les articles 20 et 21", engine, 2)
        self.assertEqual(len(engine.calls), 3)
        self.assertEqual(engine.calls[0][0], "Comparer les articles 20 et 21")
        self.assertEqual({hit["article_number"] for hit in hits}, {20, 21})
        self.assertEqual(trace["retrieval_calls"], 3)
        self.assertEqual(trace["method"], "explicit_articles")

    def test_conceptual_plan_keeps_original_and_rejects_extra_queries(self):
        class Planner:
            def plan(self, question):
                return ["Première preuve ?", "Seconde preuve ?"], {"total_tokens": 20}
        class Engine:
            calls = []
            def search(self, question, k):
                self.calls.append(question)
                return [{"passage_id": question, "article_number": len(self.calls),
                         "canonical_text": question, "score": 1.0, "rank": 1}]
        engine = Engine()
        hits, trace = retrieve_multi("Question originale ?", engine, 3, Planner())
        self.assertEqual(engine.calls, ["Question originale ?", "Première preuve ?", "Seconde preuve ?"])
        self.assertEqual(len(hits), 3)
        self.assertEqual(trace["planning_usage"], {"total_tokens": 20})
        with self.assertRaises(ValueError):
            retrieve_multi("Question originale ?", engine, 1, Planner())

    def test_local_planner_validates_model_output(self):
        planner = LocalDecomposer()
        valid = {"choices": [{"message": {"content": json.dumps({"subquestions": ["Qui décide ?"]})}}],
                 "usage": {"total_tokens": 12}}
        with patch("constitution_evidence.decomposition.urlopen", return_value=io.BytesIO(json.dumps(valid).encode())):
            subquestions, usage = planner.plan("Qui intervient et comment ?")
        self.assertEqual(subquestions, ["Qui décide ?"])
        self.assertEqual(usage["total_tokens"], 12)
        invalid = {"choices": [{"message": {"content": json.dumps({"subquestions": ["a", "b", "c"]})}}]}
        with patch("constitution_evidence.decomposition.urlopen", return_value=io.BytesIO(json.dumps(invalid).encode())):
            with self.assertRaisesRegex(GenerationError, "invalid_plan"):
                planner.plan("Question ?")

if __name__ == "__main__":
    unittest.main()
