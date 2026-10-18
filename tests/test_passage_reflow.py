import unittest

from constitution_evidence.ingestion import make_passages, validate_passages
from constitution_evidence.store import digest


class PassageReflowTests(unittest.TestCase):
    def test_ocr_blank_inside_sentence_keeps_exact_offsets_and_article_paragraph(self):
        body = "La loi protège les\n\n droits de chacun.\n\nUn autre principe s'applique."
        article = {"article_id": "test:art-1", "article_number": 1,
                   "canonical_text": body, "text_hash": digest(body),
                   "page_spans": [1], "page_segments": [{"start": 0, "end": len(body), "page": 1}]}
        passages = make_passages([article])
        self.assertEqual(len(passages), 2)
        self.assertIn("les\n\n droits", passages[0]["canonical_text"])
        self.assertEqual(passages[1]["canonical_text"], "Un autre principe s'applique.")
        validate_passages([article], passages)


if __name__ == "__main__":
    unittest.main()
