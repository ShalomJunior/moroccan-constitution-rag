import unittest

from constitution_evidence.ocr_quality import find_risks


class OcrRiskContracts(unittest.TestCase):
    def test_fused_apostrophe_candidate_is_flagged_without_marking_proper_noun(self):
        articles = [{"article_number": 27, "page_spans": [7],
                     "canonical_text": "Les fonds sont utilisés à\nFusage du public.\nFonds publics."}]
        findings = find_risks(articles)
        self.assertEqual([(row["kind"], row["text"]) for row in findings],
                         [("possible_fused_apostrophe_after_preposition", "Fusage du public.")])

    def test_article_ordinals_are_not_reported_as_mixed_ocr_tokens(self):
        articles = [{"article_number": 42, "page_spans": [10],
                     "canonical_text": "Les articles 44 (2e alinéa), 47 (1er alinéa) et 130 sont cités."}]
        self.assertEqual(find_risks(articles), [])


if __name__ == "__main__":
    unittest.main()
