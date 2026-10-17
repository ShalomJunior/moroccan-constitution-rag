import io
import json
import unittest
from unittest.mock import patch
from constitution_evidence.ingestion import make_passages, parse_articles
from constitution_evidence.local_generation import LocalGenerator, GenerationError

QUOTE = "La liberté de chaque citoyen est garantie par la Constitution."

class LocalGenerationContracts(unittest.TestCase):
    def setUp(self):
        articles = parse_articles(["Article premier\n" + QUOTE])
        self.passage = make_passages(articles)[0]
        self.generator = LocalGenerator()
        self.manifest = {"source_url": "https://example.org/source.pdf", "review_status": "unreviewed_ocr"}

    def fake_response(self, quote):
        raw = {"status": "answered", "claims": [{"text": "La liberté est garantie.",
               "passage_id": self.passage["passage_id"], "quote": quote}],
               "limitations": "", "clarification_question": ""}
        payload = {"choices": [{"message": {"content": json.dumps(raw)}}], "usage": {"prompt_tokens": 10}}
        return io.BytesIO(json.dumps(payload).encode())

    def test_citation_is_checked(self):
        with patch("constitution_evidence.local_generation.urlopen", return_value=self.fake_response(QUOTE)) as call:
            answer = self.generator.generate("Quelle liberté ?", [self.passage], self.manifest)
            body = json.loads(call.call_args.args[0].data)
        self.assertEqual(body["response_format"]["type"], "json_schema")
        self.assertEqual(answer["status"], "partially_answered")
        self.assertEqual(answer["claims"][0]["evidence_spans"][0]["quote"], QUOTE)

    def test_invented_quote_rejected(self):
        with patch("constitution_evidence.local_generation.urlopen", return_value=self.fake_response("invented")):
            with self.assertRaises(GenerationError):
                self.generator.generate("Quelle liberté ?", [self.passage], self.manifest)

if __name__ == "__main__":
    unittest.main()
