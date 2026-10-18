import unittest
from constitution_evidence.ingestion import make_passages, parse_articles
from constitution_evidence.references import ReferenceExpander, extract_reference_edges

class ReferenceContracts(unittest.TestCase):
    def setUp(self):
        self.articles = parse_articles([
            "PRÉAMBULE\nTexte introductif.\n"
            "Article premier\nLes règles de nomination suivent les conditions de l'article 2.\n"
            "Article 2\nLe conseil prend sa décision selon la procédure prévue ici.\n"
            "Article 3\nCette disposition traite d'un autre domaine sans renvoi."
        ])
        self.passages = make_passages(self.articles)

    def test_edge_has_exact_provenance_and_valid_target(self):
        edges = extract_reference_edges(self.articles)
        self.assertEqual([(e["from_article"], e["to_article"]) for e in edges], [(1, 2)])
        article = self.articles[1]
        edge = edges[0]
        self.assertEqual(article["canonical_text"][edge["reference_start"]:edge["reference_end"]],
                         edge["reference_quote"])

    def test_one_hop_expansion_is_bounded_and_traceable(self):
        first = next(p for p in self.passages if p["article_number"] == 1)
        other = next(p for p in self.passages if p["article_number"] == 3)
        class Base:
            def search(self, question, k):
                return [{**first, "rank": 1, "score": 2.0}, {**other, "rank": 2, "score": 1.0}][:k]
        engine = ReferenceExpander(Base(), self.articles, self.passages)
        hits = engine.search("Quelles règles de nomination ?", 2)
        self.assertEqual([h["article_number"] for h in hits], [1, 2])
        self.assertEqual(hits[1]["retriever"], "reference_expansion")
        reference = hits[1]["reference"]
        self.assertEqual(reference["source_passage_id"], first["passage_id"])
        self.assertEqual(first["canonical_text"][reference["source_quote_start"]:reference["source_quote_end"]],
                         reference["reference_quote"])
        self.assertEqual([h["article_number"] for h in engine.search("articles 1 et 3", 2)], [1, 3])

if __name__ == "__main__":
    unittest.main()
