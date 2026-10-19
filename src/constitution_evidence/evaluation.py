"""Article and evidence-span retrieval evaluation with resumable run artifacts."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from . import retrieval
from .evidence import pack
from .retrieval import BM25, Dense, Hybrid
from .store import read_jsonl, write_jsonl, digest

def unique_articles(hits: list[dict]) -> list[int]:
    return list(dict.fromkeys(h["article_number"] for h in hits))

def _span_covered(span: dict, hits: list[dict]) -> bool:
    """Gold offsets use canonical passage text, not parent article text."""
    return any(h["passage_id"] == span["passage_id"] and
               0 <= span["char_start"] < span["char_end"] <= len(h["canonical_text"])
               for h in hits)

def score_retrieval(hits: list[dict], relevant: list[int], k: int = 10,
                    evidence_sets: list[list[dict]] | None = None,
                    relevant_spans: list[dict] | None = None,
                    context_hits: list[dict] | None = None) -> dict:
    if k <= 0:
        raise ValueError("k must be positive")
    ranked = unique_articles(hits)[:k]
    candidate_hits = []
    seen_articles = set()
    for hit in hits:
        if hit["article_number"] not in seen_articles and len(seen_articles) >= k:
            break
        candidate_hits.append(hit)
        seen_articles.add(hit["article_number"])
    gold = set(relevant)
    found = gold.intersection(ranked)
    first = next((i for i, a in enumerate(ranked, 1) if a in gold), None)
    result = {"recall": len(found) / len(gold) if gold else None,
              "mrr": 1 / first if first else (0.0 if gold else None),
              "complete_evidence": None, "span_recall": None,
              "context_evidence_coverage": None}
    if evidence_sets is not None:
        if not evidence_sets or any(not group for group in evidence_sets):
            raise ValueError("Evidence sets must contain nonempty alternatives")
        result["complete_evidence"] = int(any(all(_span_covered(span, candidate_hits) for span in group)
                                               for group in evidence_sets))
    if relevant_spans is not None:
        if not relevant_spans:
            raise ValueError("Relevant spans must be nonempty when supplied")
        result["span_recall"] = sum(_span_covered(span, candidate_hits) for span in relevant_spans) / len(relevant_spans)
        if context_hits is not None:
            result["context_evidence_coverage"] = sum(_span_covered(span, context_hits) for span in relevant_spans) / len(relevant_spans)
    return result

def _git_state(repo: Path) -> dict:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}

def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = stream.name
    os.replace(temporary, path)

def evaluate(questions_path: Path, passages_path: Path, split: str, output_dir: Path,
             k: int = 10, strategy: str = "bm25", context_chars: int = 7000) -> dict:
    if k <= 0 or context_chars <= 0:
        raise ValueError("k and context_chars must be positive")
    all_questions = read_jsonl(questions_path)
    families = {}
    for q in all_questions:
        family = q["family_id"]
        if family in families and families[family] != q["split"]:
            raise ValueError(f"Family crosses splits: {family}")
        families[family] = q["split"]
    questions = [q for q in all_questions if q["split"] == split]
    if not questions:
        raise ValueError(f"No questions in split {split}")
    ids = [q["question_id"] for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate question IDs")
    records = read_jsonl(passages_path)
    by_id = {p["passage_id"]: p for p in records}
    for question in questions:
        spans = question.get("relevant_spans", [])
        groups = question.get("acceptable_evidence_sets", [])
        for span in spans + [span for group in groups for span in group]:
            passage = by_id.get(span["passage_id"])
            if passage is None or not 0 <= span["char_start"] < span["char_end"] <= len(passage["canonical_text"]):
                raise ValueError(f"Invalid gold span in {question['question_id']}: {span}")
    expected = {"split": split, "article_k": k, "context_chars": context_chars,
                "question_count": len(questions), "question_ids": ids,
                "questions_sha256": digest(questions_path.read_bytes()),
                "passages_sha256": digest(passages_path.read_bytes()),
                "evaluation_code_sha256": digest(Path(__file__).read_bytes()),
                "retrieval_code_sha256": digest(Path(retrieval.__file__).read_bytes()),
                "method": strategy, "status": "retrieval_only"}
    manifest_path = output_dir / "manifest.json"
    rows_path = output_dir / "retrieval.jsonl"
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text())
        if any(prior.get(key) != value for key, value in expected.items()):
            raise ValueError("Run ID already belongs to different inputs or configuration")
    elif rows_path.exists():
        raise ValueError("Run output exists without a manifest")
    else:
        expected["git"] = _git_state(passages_path.resolve().parents[2])
        _atomic_json(manifest_path, expected)
    done_rows = read_jsonl(rows_path) if rows_path.exists() else []
    done = {row["question_id"]: row for row in done_rows}
    if len(done) != len(done_rows) or not set(done) <= set(ids):
        raise ValueError("Existing run contains duplicate or unknown question IDs")
    remaining = [q for q in questions if q["question_id"] not in done]
    if remaining:
        if strategy == "bm25":
            engine = BM25(records)
        elif strategy == "dense":
            engine = Dense(records, index_dir=passages_path.parent / "dense-index")
        elif strategy in {"hybrid", "hybrid-rerank"}:
            engine = Hybrid(records, index_dir=passages_path.parent / "dense-index", rerank=strategy == "hybrid-rerank")
        else:
            raise ValueError(f"Unknown retrieval strategy: {strategy}")
        for question in remaining:
            depth = min(len(records), max(10 * k, 100))
            hits = (engine.search(question["question"], depth, lexical_k=depth, dense_k=depth)
                    if isinstance(engine, Hybrid) else engine.search(question["question"], depth))
            context = pack(hits[:k], context_chars)
            metrics = score_retrieval(hits, question.get("relevant_articles", []), k,
                                      question.get("acceptable_evidence_sets") or None,
                                      question.get("relevant_spans") or None, context)
            done[question["question_id"]] = {
                "question_id": question["question_id"], "family_id": question["family_id"], "split": split,
                "variant_type": question.get("variant_type", "unspecified"),
                "passage_depth": depth, "hits": [{"passage_id": h["passage_id"], "article_number": h["article_number"],
                                                  "score": h["score"]} for h in hits],
                "context_passage_ids": [h["passage_id"] for h in context], "metrics": metrics}
            write_jsonl(rows_path, [done[qid] for qid in ids if qid in done])
    return report(output_dir)

def report(output_dir: Path) -> dict:
    rows = read_jsonl(output_dir / "retrieval.jsonl")
    manifest = json.loads((output_dir / "manifest.json").read_text())
    ids = [row["question_id"] for row in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= set(manifest.get("question_ids", ids)):
        raise ValueError("Run rows do not match the manifest")
    keys = ("recall", "mrr", "complete_evidence", "span_recall", "context_evidence_coverage")
    summary = {"questions": len(rows), "expected_questions": manifest["question_count"],
               "complete_run": len(rows) == manifest["question_count"]}
    for key in keys:
        values = [r["metrics"][key] for r in rows if r["metrics"].get(key) is not None]
        summary[key] = sum(values) / len(values) if values else None
        summary[key + "_n"] = len(values)
    if "evaluation_code_sha256" not in manifest:
        summary["legacy_article_coverage"] = summary["complete_evidence"]
        summary["complete_evidence"] = None
        summary["complete_evidence_n"] = 0
        summary["note"] = "Legacy runs used article coverage as an evidence proxy; no span evidence was scored."
    variants = sorted({row.get("variant_type", "unspecified") for row in rows})
    summary["by_variant"] = {}
    for variant in variants:
        subset = [row["metrics"] for row in rows if row.get("variant_type", "unspecified") == variant]
        scored = [item for item in subset if item.get("recall") is not None]
        summary["by_variant"][variant] = {
            "questions": len(subset), "with_evidence": len(scored),
            "recall": sum(item["recall"] for item in scored) / len(scored) if scored else None,
            "mrr": sum(item["mrr"] for item in scored) / len(scored) if scored else None}
    _atomic_json(output_dir / "metrics.json", summary)
    return summary
