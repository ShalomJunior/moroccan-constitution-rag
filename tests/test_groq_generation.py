import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from constitution_evidence.api import AskRequest, ask
from constitution_evidence.groq_generation import GroqDecomposer, GroqGenerator
from constitution_evidence.generation import GenerationError
from constitution_evidence.ingestion import make_passages, parse_articles


class FakeClient:
    def __init__(self, content):
        self.content = content
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(self.content)))],
            usage=SimpleNamespace(model_dump=lambda: {"prompt_tokens": 10, "completion_tokens": 15,
                                                           "total_tokens": 25}))


class GroqContracts(unittest.TestCase):
    def setUp(self):
        self.quote = "La liberté de chaque citoyen est garantie par la Constitution."
        self.passage = make_passages(parse_articles(["Article premier\n" + self.quote]))[0]
        self.manifest = {"source_url": "https://example.org/source.pdf", "review_status": "unreviewed_ocr"}

    def test_strict_schema_and_citation_validation(self):
        raw = {"status": "answered", "claims": [{"text": "La liberté est garantie.",
               "passage_id": self.passage["passage_id"], "quote": self.quote}],
               "limitations": "", "clarification_question": ""}
        client = FakeClient(raw)
        answer = GroqGenerator(client=client).generate("Quelle liberté ?", [self.passage], self.manifest)
        call = client.calls[0]
        self.assertTrue(call["response_format"]["json_schema"]["strict"])
        self.assertEqual(call["reasoning_effort"], "low")
        self.assertEqual(call["max_completion_tokens"], 2048)
        self.assertEqual(answer["status"], "partially_answered")
        self.assertEqual(answer["claims"][0]["evidence_spans"][0]["quote"], self.quote)
        raw["claims"][0]["quote"] = "invented"
        with self.assertRaises(GenerationError):
            GroqGenerator(client=FakeClient(raw)).generate("Quelle liberté ?", [self.passage], self.manifest)

    def test_line_break_in_source_is_preserved_in_validated_quote(self):
        passage = {**self.passage, "canonical_text": "Le droit à la vie.\nLa loi protège ce droit."}
        raw = {"status": "answered", "claims": [{"text": "La loi protège ce droit.",
               "passage_id": passage["passage_id"], "quote": "Le droit à la vie. La loi protège ce droit."}],
               "limitations": "", "clarification_question": ""}
        answer = GroqGenerator(client=FakeClient(raw)).generate("Que dit le texte ?", [passage], self.manifest)
        self.assertEqual(answer["claims"][0]["evidence_spans"][0]["quote"], passage["canonical_text"])

    def test_claim_can_cite_intro_and_list_item(self):
        intro = {**self.passage, "canonical_text": "Le Conseil délibère sur les questions suivantes :"}
        bullet = {**self.passage, "passage_id": self.passage["passage_id"] + ":p-2",
                  "canonical_text": "- les orientations stratégiques ;"}
        raw = {"status": "answered", "claims": [{"text": "Le Conseil délibère sur les orientations stratégiques.",
               "evidence": [{"passage_id": intro["passage_id"], "quote": intro["canonical_text"]},
                            {"passage_id": bullet["passage_id"], "quote": bullet["canonical_text"]}]}],
               "limitations": "None", "clarification_question": ""}
        answer = GroqGenerator(client=FakeClient(raw)).generate("Qui décide ?", [intro, bullet], self.manifest)
        self.assertEqual(len(answer["claims"][0]["evidence_spans"]), 2)
        self.assertEqual(len(answer["sources"]), 2)
        self.assertEqual(answer["limitations"], "Texte OCR non relu ; les affirmations et leur pertinence juridique ne sont pas validées.")

    def test_truncated_structured_output_retries_once_with_larger_budget(self):
        raw = {"status": "answered", "claims": [{"text": "La liberté est garantie.",
               "passage_id": self.passage["passage_id"], "quote": self.quote}],
               "limitations": "", "clarification_question": ""}
        client = FakeClient(raw)
        original_create = client.create
        def create(**kwargs):
            if not client.calls:
                client.calls.append(kwargs)
                raise GenerationError("groq_output_truncated")
            return original_create(**kwargs)
        client.chat.completions.create = create
        answer = GroqGenerator(client=client).generate("Quelle liberté ?", [self.passage], self.manifest)
        self.assertEqual(answer["provider_attempts"], 2)
        self.assertEqual([call["max_completion_tokens"] for call in client.calls], [2048, 4096])

    def test_invalid_quote_gets_one_bounded_repair_attempt(self):
        raw = {"status": "answered", "claims": [{"text": "La liberté est garantie.",
               "passage_id": self.passage["passage_id"], "quote": "invented"}],
               "limitations": "", "clarification_question": ""}
        client = FakeClient(raw)
        original_create = client.create
        def create(**kwargs):
            if client.calls:
                client.content = {**raw, "claims": [{**raw["claims"][0], "quote": self.quote}]}
            return original_create(**kwargs)
        client.chat.completions.create = create
        answer = GroqGenerator(client=client).generate("Quelle liberté ?", [self.passage], self.manifest)
        self.assertEqual(answer["provider_attempts"], 2)
        self.assertEqual(answer["usage"]["total_tokens"], 50)
        self.assertEqual(answer["claims"][0]["evidence_spans"][0]["quote"], self.quote)
        self.assertEqual(len(client.calls), 2)

    def test_missing_key_and_plan(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            with patch("dotenv.load_dotenv"):
                with self.assertRaisesRegex(GenerationError, "groq_api_key_missing"):
                    GroqGenerator()
        client = FakeClient({"subquestions": ["article 20 liberté", "article 21 sécurité"]})
        plan, usage = GroqDecomposer(client=client).plan("Comment les droits sont-ils protégés ?")
        self.assertEqual(len(plan), 2)
        self.assertEqual(usage["prompt_tokens"], 10)
        self.assertTrue(client.calls[0]["response_format"]["json_schema"]["strict"])

    def test_api_selects_groq_without_local_server(self):
        raw = {"status": "answered", "claims": [{"text": "La liberté est garantie.",
               "passage_id": self.passage["passage_id"], "quote": self.quote}],
               "limitations": "", "clarification_question": ""}
        generator = GroqGenerator(client=FakeClient(raw))
        engine = SimpleNamespace(search=lambda question, top_k: [self.passage])
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_corpus", return_value=(None, self.manifest, {})):
                with patch("constitution_evidence.api._engine", return_value=engine):
                    with patch("constitution_evidence.groq_generation.GroqGenerator", return_value=generator):
                        answer = ask(AskRequest(question="article 1", generator="groq"))
        self.assertEqual(answer["model"], generator.model)
        self.assertEqual(answer["claims"][0]["evidence_spans"][0]["quote"], self.quote)


if __name__ == "__main__":
    unittest.main()
