import unittest

from constitution_evidence.evidence import pack_with_article_leads


class ContextLeadContracts(unittest.TestCase):
    def test_opening_paragraph_is_added_without_losing_ranked_hit(self):
        lead = {"passage_id": "a:p-1", "article_number": 47, "paragraph_index": 1,
                "canonical_text": "Le Roi nomme le Chef du Gouvernement."}
        hit = {"passage_id": "a:p-2", "article_number": 47, "paragraph_index": 2,
               "canonical_text": "Sur proposition du Chef du Gouvernement...", "score": 1.0}
        context = pack_with_article_leads([hit], [lead, hit], 100)
        self.assertEqual([p["passage_id"] for p in context], ["a:p-1", "a:p-2"])
        self.assertLessEqual(sum(len(p["canonical_text"]) for p in context), 100)
        self.assertEqual(pack_with_article_leads([hit], [lead, hit], 45), [hit])

    def test_following_paragraph_supplies_conditions(self):
        lead = {"passage_id": "a:p-1", "article_number": 27, "paragraph_index": 1,
                "canonical_text": "Droit d'accès à l'information."}
        limit = {"passage_id": "a:p-2", "article_number": 27, "paragraph_index": 2,
                 "canonical_text": "Ce droit peut être limité par la loi."}
        context = pack_with_article_leads([lead], [lead, limit], 100)
        self.assertEqual([p["passage_id"] for p in context], ["a:p-1", "a:p-2"])
        self.assertEqual(context[1]["retriever"], "article_context")


if __name__ == "__main__":
    unittest.main()
