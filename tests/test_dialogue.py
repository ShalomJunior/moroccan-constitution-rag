import json
import unittest
from pathlib import Path
from unittest.mock import patch
from constitution_evidence.api import AskRequest, DialogueTurn, ask
from constitution_evidence.dialogue import resolve, next_articles


class DialogueTests(unittest.TestCase):
    def test_followup_and_topic_change(self):
        history = [{"article_numbers": [20]}]
        self.assertEqual(resolve("Que dit cet article ?", history)["resolved_question"], "Que dit l'article 20 ?")
        self.assertEqual(resolve("Que dit l'article 21 ?", history)["resolved_question"], "Que dit l'article 21 ?")
        self.assertTrue(resolve("Que dit cet article ?", [])["needs_clarification"])
        self.assertTrue(resolve("Que dit cet article ?", [{"article_numbers": [20, 21]}])["needs_clarification"])
        self.assertEqual(next_articles("Que disent les articles 20 et 21 ?", []), [20, 21])

    def test_sessions_are_stateless_and_followup_retrieves_again(self):
        calls = []
        class Engine:
            def search(self, query, top_k):
                calls.append(query)
                return []
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_corpus", return_value=(None, {"source_url": "https://example.org/a.pdf"}, {})):
                with patch("constitution_evidence.api._engine", return_value=Engine()):
                    first = ask(AskRequest(question="Que dit cet article ?", history=[DialogueTurn(article_numbers=[20])]))
                    second = ask(AskRequest(question="Que dit cet article ?"))
        self.assertEqual(calls, ["Que dit l'article 20 ?"])
        self.assertEqual(first["status"], "insufficient_evidence")
        self.assertEqual(second["status"], "needs_clarification")

    def test_history_is_bounded(self):
        with self.assertRaises(ValueError):
            AskRequest(question="Question", history=[DialogueTurn(article_numbers=[1])] * 4)

    def test_local_mode_without_hits_abstains(self):
        class Engine:
            def search(self, query, top_k):
                return []
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_corpus", return_value=(None, {"source_url": "https://example.org/a.pdf"}, {})):
                with patch("constitution_evidence.api._engine", return_value=Engine()):
                    answer = ask(AskRequest(question="article 1", generator="local"))
        self.assertEqual(answer["status"], "insufficient_evidence")

    def test_provisional_dialogue_fixtures(self):
        path = Path(__file__).resolve().parents[1] / "data/annotations/dialogue_calibration.jsonl"
        fixtures = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(fixtures), 15)
        for fixture in fixtures:
            for turn in fixture["turns"]:
                result = resolve(turn["question"], turn["history"])
                self.assertEqual(result["needs_clarification"], turn["expected_state"] == "needs_clarification")
                if "expected_resolved_question" in turn:
                    self.assertEqual(result["resolved_question"], turn["expected_resolved_question"])


if __name__ == "__main__":
    unittest.main()
