"""One-hop expansion through article references written in the source text."""
from collections import defaultdict
from .retrieval import ARTICLE_LIST, ARTICLE_QUERY, BM25, explicit_article_numbers

def extract_reference_edges(articles: list[dict], review_status: str = "unreviewed_ocr") -> list[dict]:
    valid = {a["article_number"] for a in articles if a["article_number"] > 0}
    edges = []
    seen = set()
    for article in articles:
        source = article["article_number"]
        if source == 0:
            continue
        body = article["canonical_text"]
        for pattern in (ARTICLE_LIST, ARTICLE_QUERY):
            for match in pattern.finditer(body):
                quote = match.group(0)
                for target in explicit_article_numbers(quote):
                    key = (source, target, match.start())
                    if target not in valid or target == source or key in seen:
                        continue
                    seen.add(key)
                    edges.append({"from_article": source, "to_article": target,
                                  "reference_quote": quote, "reference_start": match.start(),
                                  "reference_end": match.end(), "source_hash": article["text_hash"],
                                  "review_status": review_status})
    return sorted(edges, key=lambda edge: (edge["from_article"], edge["reference_start"], edge["to_article"]))

class ReferenceExpander:
    """Reserve at most one result for a cited article when its reference is in a hit."""
    def __init__(self, base, articles: list[dict], passages: list[dict], max_added: int = 1,
                 review_status: str = "unreviewed_ocr"):
        if max_added < 1:
            raise ValueError("max_added must be positive")
        self.base = base
        self.max_added = max_added
        self.selector = BM25(passages)
        self.edges = defaultdict(list)
        for edge in extract_reference_edges(articles, review_status):
            self.edges[edge["from_article"]].append(edge)

    def search(self, question: str, k: int = 5) -> list[dict]:
        hits = self.base.search(question, k)
        if k < 2 or len(explicit_article_numbers(question)) > 1:
            return hits
        reserve = min(self.max_added, k - 1)
        kept = hits[:k - reserve]
        present_articles = {hit["article_number"] for hit in hits}
        added = []
        for hit in kept:
            for edge in self.edges.get(hit["article_number"], []):
                if not (hit["char_start"] <= edge["reference_start"] < edge["reference_end"] <= hit["char_end"]):
                    continue
                target = edge["to_article"]
                if target in present_articles:
                    continue
                selected = self.selector.search(f"article {target} {question}", 1)
                if not selected or selected[0]["article_number"] != target:
                    continue
                added.append({**selected[0], "retriever": "reference_expansion",
                              "reference": {**edge, "source_passage_id": hit["passage_id"],
                                            "source_quote_start": edge["reference_start"] - hit["char_start"],
                                            "source_quote_end": edge["reference_end"] - hit["char_start"]}})
                present_articles.add(target)
                if len(added) == reserve:
                    break
            if len(added) == reserve:
                break
        if not added:
            return hits
        combined = (kept + added + hits[len(kept):])[:k]
        return [{**hit, "rank": rank} for rank, hit in enumerate(combined, 1)]
