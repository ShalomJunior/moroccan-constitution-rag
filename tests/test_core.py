import unittest
from constitution_evidence.ingestion import parse_articles, validate_articles, make_passages
from constitution_evidence.retrieval import BM25
from constitution_evidence.evidence import extractive_answer, validate_answer
from constitution_evidence.evaluation import score_retrieval

class Contracts(unittest.TestCase):
    def setUp(self):
        self.articles = parse_articles(["PRÉAMBULE\nTexte introductif\nArticle premier\nLa liberté de chaque citoyen est garantie par la Constitution.\nArticle 2\nLa justice de chaque citoyen est garantie par la Constitution."])
        self.passages = make_passages(self.articles)

    def test_article_boundary_and_inventory(self):
        self.assertEqual([a["article_number"] for a in self.articles], [0, 1, 2])
        validate_articles(self.articles, 2)
        with self.assertRaises(ValueError):
            validate_articles(self.articles, 3)

    def test_lookup_and_citation(self):
        hits = BM25(self.passages).search("article 2", 2)
        self.assertEqual(hits[0]["article_number"], 2)
        answer = extractive_answer(hits, {"source_url": "https://example.org/source.pdf"})
        self.assertEqual(answer["status"], "partially_answered")
        answer["claims"][0]["evidence_spans"][0]["quote"] = "invented"
        with self.assertRaises(ValueError):
            validate_answer(answer, hits)

    def test_article_dedup_and_cutoff(self):
        hits = [{"article_number": n} for n in [1] * 3 + list(range(2, 11)) + [11]]
        self.assertEqual(score_retrieval(hits, [11], 10)["mrr"], 0)

if __name__ == "__main__":
    unittest.main()
