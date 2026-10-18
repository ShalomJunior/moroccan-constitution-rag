import io
import json
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch
from constitution_evidence.local_generation import LocalGenerator
from constitution_evidence.generation import GenerationError


class LocalRetryTests(unittest.TestCase):
    def test_transient_failure_retries_once(self):
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": json.dumps({
            "status": "insufficient_evidence", "claims": [], "limitations": "", "clarification_question": ""})}}]}).encode())
        passage = {"passage_id": "p1", "canonical_text": "Texte.", "text_hash": "hash",
                   "article_number": 1, "page_spans": [1]}
        with patch("constitution_evidence.local_generation.urlopen", side_effect=[URLError("down"), response]) as opener:
            answer = LocalGenerator().generate("Question ?", [passage], {"source_url": "https://example.org/a.pdf"})
        self.assertEqual(opener.call_count, 2)
        self.assertEqual(answer["provider_attempts"], 2)

    def test_nontransient_http_error_does_not_retry(self):
        passage = {"passage_id": "p1", "canonical_text": "Texte."}
        error = HTTPError("http://127.0.0.1:8080", 400, "bad request", {}, None)
        with patch("constitution_evidence.local_generation.urlopen", side_effect=error) as opener:
            with self.assertRaises(GenerationError):
                LocalGenerator().generate("Question ?", [passage], {})
        self.assertEqual(opener.call_count, 1)


if __name__ == "__main__":
    unittest.main()
