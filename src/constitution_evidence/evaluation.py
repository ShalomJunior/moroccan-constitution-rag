"""Retrieval metrics at canonical article level; no test tuning."""
import json
from pathlib import Path
from .retrieval import BM25, Dense, Hybrid
from .store import read_jsonl, write_jsonl, digest

def unique_articles(hits: list[dict]) -> list[int]:
    return list(dict.fromkeys(h["article_number"] for h in hits))

def score_retrieval(hits: list[dict], relevant: list[int], k: int = 10) -> dict:
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant:
        return {"recall": None, "mrr": None, "complete_evidence": None}
    ranked = unique_articles(hits)[:k]
    gold = set(relevant)
    found = gold.intersection(ranked)
    first = next((i for i, a in enumerate(ranked, 1) if a in gold), None)
    return {"recall": len(found) / len(gold), "mrr": 1 / first if first else 0.0,
            "complete_evidence": int(gold <= set(ranked))}

def evaluate(questions_path: Path, passages_path: Path, split: str, output_dir: Path, k: int = 10, strategy: str = "bm25") -> dict:
    questions = [q for q in read_jsonl(questions_path) if q["split"] == split]
    if not questions:
        raise ValueError(f"No questions in split {split}")
    records = read_jsonl(passages_path)
    if strategy == "bm25":
        engine = BM25(records)
    elif strategy == "dense":
        engine = Dense(records, index_dir=passages_path.parent / "dense-index")
    elif strategy in {"hybrid", "hybrid-rerank"}:
        engine = Hybrid(records, index_dir=passages_path.parent / "dense-index", rerank=strategy == "hybrid-rerank")
    else:
        raise ValueError(f"Unknown retrieval strategy: {strategy}")
    rows = []
    for question in questions:
        depth = min(len(records), max(10 * k, 100))
        if isinstance(engine, Hybrid):
            hits = engine.search(question["question"], depth, lexical_k=depth, dense_k=depth)
        else:
            hits = engine.search(question["question"], depth)
        metrics = score_retrieval(hits, question.get("relevant_articles", []), k)
        rows.append({"question_id": question["question_id"], "family_id": question["family_id"],
                     "split": split, "hits": [{"passage_id": h["passage_id"], "article_number": h["article_number"], "score": h["score"]} for h in hits],
                     "metrics": metrics})
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "retrieval.jsonl", rows)
    manifest = {"split": split, "article_k": k, "passage_depth": depth, "question_count": len(questions),
                "questions_sha256": digest(questions_path.read_bytes()), "passages_sha256": digest(passages_path.read_bytes()),
                "method": strategy, "status": "retrieval_only"}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return report(output_dir)

def report(output_dir: Path) -> dict:
    rows = read_jsonl(output_dir / "retrieval.jsonl")
    scored = [r["metrics"] for r in rows if r["metrics"]["recall"] is not None]
    summary = {"questions": len(rows), "with_evidence": len(scored),
               **{key: (sum(m[key] for m in scored) / len(scored) if scored else None)
                  for key in ("recall", "mrr", "complete_evidence")}}
    (output_dir / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
