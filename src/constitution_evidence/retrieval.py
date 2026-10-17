"""Adapters for maintained lexical and dense retrieval libraries."""
import re
import unicodedata
from collections import Counter
import bm25s

ARTICLE_QUERY = re.compile(r"\barticles?\s+(\d{1,3})\b", re.IGNORECASE)
ARTICLE_LIST = re.compile(r"\barticles\s+(\d{1,3}(?:(?:\s*(?:,|;|et|ou)\s*)\d{1,3})*)", re.IGNORECASE)
PREAMBLE_QUERY = re.compile(r"\bpr[ée]ambule\b", re.IGNORECASE)

def explicit_article_numbers(question: str) -> list[int]:
    """Return named article numbers, including simple French article lists."""
    matches = [(match.start(), int(match.group(1))) for match in ARTICLE_QUERY.finditer(question)]
    for match in ARTICLE_LIST.finditer(question):
        for number in re.findall(r"\d{1,3}", match.group(1)):
            matches.append((match.start(), int(number)))
    ordered = []
    for _, number in sorted(matches):
        if 1 <= number <= 180 and number not in ordered:
            ordered.append(number)
    return ordered

def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))

class BM25:
    def __init__(self, passages: list[dict]):
        self.passages = passages
        self.index = bm25s.BM25(method="lucene")
        self.index.index(bm25s.tokenize([normalize(p["canonical_text"]) for p in passages], stopwords=None, show_progress=False), show_progress=False)

    def search(self, question: str, k: int = 5) -> list[dict]:
        if not question.strip() or k <= 0:
            raise ValueError("Question must be nonempty and k must be positive")
        if not self.passages:
            return []
        wanted = explicit_article_numbers(question)
        if not wanted and PREAMBLE_QUERY.search(question):
            wanted = [0]
        query_tokens = bm25s.tokenize(normalize(question), stopwords=None, show_progress=False)
        if wanted:
            ids, scores = self.index.retrieve(query_tokens, k=len(self.passages), show_progress=False)
            lexical_scores = {int(index): float(score) for index, score in zip(ids[0], scores[0])}
            groups = []
            for number in wanted:
                candidates = [(lexical_scores.get(i, 0.0), p) for i, p in enumerate(self.passages)
                              if p["article_number"] == number]
                candidates.sort(key=lambda row: (-row[0], row[1]["paragraph_index"]))
                if candidates:
                    groups.append(candidates)
            if groups:
                ordered = []
                for offset in range(max(map(len, groups))):
                    for group in groups:
                        if offset < len(group):
                            ordered.append(group[offset])
                            if len(ordered) == k:
                                break
                    if len(ordered) == k:
                        break
                return [{**p, "score": round(score, 6), "rank": rank, "retriever": "article_lookup"}
                        for rank, (score, p) in enumerate(ordered, 1)]
        ids, scores = self.index.retrieve(query_tokens, k=min(len(self.passages), max(k, 20)), show_progress=False)
        ranked = {}
        for index, score in zip(ids[0], scores[0]):
            if score > 0:
                p = self.passages[int(index)]
                ranked[p["passage_id"]] = (float(score), p)
        ordered = sorted(ranked.values(), key=lambda row: (-row[0], row[1]["passage_id"]))[:k]
        return [{**p, "score": round(score, 6), "rank": rank, "retriever": "bm25s"}
                for rank, (score, p) in enumerate(ordered, 1)]

class Dense:
    """Exact cosine search with FastEmbed ONNX embeddings and FAISS IndexFlatIP."""
    def __init__(self, passages: list[dict], model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", index_dir=None):
        try:
            import faiss
            import numpy as np
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError("Install the dense extra: pip install -e '.[dense]'") from exc
        from pathlib import Path
        import json
        from .store import digest
        if not passages:
            raise ValueError("Dense index needs passages")
        self.faiss = faiss
        self.np = np
        self.passages = passages
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)
        self.corpus_hash = digest("\n".join(p["passage_id"] + p["text_hash"] for p in passages))
        index_dir = Path(index_dir) if index_dir else None
        meta_path = index_dir / "metadata.json" if index_dir else None
        index_path = index_dir / "index.faiss" if index_dir else None
        if meta_path and meta_path.exists() and index_path.exists():
            meta = json.loads(meta_path.read_text())
            if meta == {"corpus_hash": self.corpus_hash, "model_name": model_name}:
                self.index = faiss.read_index(str(index_path))
                if self.index.ntotal == len(passages):
                    return
        vectors = np.asarray(list(self.model.passage_embed([p["canonical_text"] for p in passages])), dtype="float32")
        faiss.normalize_L2(vectors)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        if index_dir:
            index_dir.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(index_path))
            meta_path.write_text(json.dumps({"corpus_hash": self.corpus_hash, "model_name": model_name}, indent=2) + "\n")

    def search(self, question: str, k: int = 5) -> list[dict]:
        if not question.strip() or k <= 0:
            raise ValueError("Question must be nonempty and k must be positive")
        query = self.np.asarray(list(self.model.query_embed([question])), dtype="float32")
        self.faiss.normalize_L2(query)
        scores, indices = self.index.search(query, min(k, len(self.passages)))
        rows = [(float(score), self.passages[int(index)]) for score, index in zip(scores[0], indices[0]) if index >= 0]
        rows.sort(key=lambda row: (-row[0], row[1]["passage_id"]))
        return [{**p, "score": round(score, 6), "rank": rank, "retriever": "fastembed-faiss"}
                for rank, (score, p) in enumerate(rows, 1)]

def rrf(lists: list[list[dict]], k: int = 5, constant: int = 60) -> list[dict]:
    scores, items = Counter(), {}
    for hits in lists:
        for rank, hit in enumerate(hits, 1):
            pid = hit["passage_id"]
            scores[pid] += 1 / (constant + rank)
            items[pid] = hit
    return [{**items[pid], "score": round(score, 8), "rank": rank, "retriever": "rrf"}
            for rank, (pid, score) in enumerate(sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:k], 1)]


class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError as exc:
            raise RuntimeError("Install the dense extra: pip install -e '.[dense]'") from exc
        self.model = TextCrossEncoder(model_name=model_name)
        self.model_name = model_name

    def rerank(self, question: str, hits: list[dict], k: int = 5) -> list[dict]:
        if not hits:
            return []
        scores = list(self.model.rerank(question, [h["canonical_text"] for h in hits]))
        rows = sorted(zip(scores, hits), key=lambda row: (-float(row[0]), row[1]["passage_id"]))[:k]
        return [{**hit, "score": float(score), "rank": rank, "retriever": "fastembed-cross-encoder"}
                for rank, (score, hit) in enumerate(rows, 1)]

class Hybrid:
    def __init__(self, passages: list[dict], index_dir=None, rerank: bool = False):
        self.lexical = BM25(passages)
        self.passages = passages
        self.index_dir = index_dir
        self.dense = None
        self.rerank_enabled = rerank
        self.reranker = None

    def search(self, question: str, k: int = 5, lexical_k: int = 20, dense_k: int = 20) -> list[dict]:
        if explicit_article_numbers(question) or PREAMBLE_QUERY.search(question):
            direct = self.lexical.search(question, k)
            if direct and direct[0]["retriever"] == "article_lookup":
                return direct
        if self.dense is None:
            self.dense = Dense(self.passages, index_dir=self.index_dir)
        candidates = rrf([self.lexical.search(question, lexical_k), self.dense.search(question, dense_k)], k=max(k, 20))
        if self.rerank_enabled and self.reranker is None:
            self.reranker = Reranker()
        return self.reranker.rerank(question, candidates, k) if self.reranker else candidates[:k]
