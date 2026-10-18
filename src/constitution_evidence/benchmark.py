"""Reproducible local retrieval latency measurements."""
import json
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .retrieval import BM25, Dense, Hybrid
from .store import digest, read_jsonl
from .evidence import pack
from .local_generation import LocalGenerator


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("No timing observations")
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 3)


def measure_retrieval(questions_path: Path, passages_path: Path, strategy: str = "bm25",
                      repeat: int = 3, concurrency: int = 2, k: int = 5) -> dict:
    if not 1 <= repeat <= 10 or not 1 <= concurrency <= 4 or not 1 <= k <= 20:
        raise ValueError("repeat, concurrency, or k exceeds the benchmark budget")
    questions = [q for q in read_jsonl(questions_path) if q.get("split") == "dev"]
    if not questions or len({q["question_id"] for q in questions}) != len(questions):
        raise ValueError("Benchmark needs distinct development questions")
    passages = read_jsonl(passages_path)
    started = time.perf_counter()
    if strategy == "bm25":
        engine = BM25(passages)
    elif strategy == "dense":
        engine = Dense(passages, index_dir=passages_path.parent / "dense-index")
    elif strategy in {"hybrid", "hybrid-rerank"}:
        engine = Hybrid(passages, index_dir=passages_path.parent / "dense-index",
                        rerank=strategy == "hybrid-rerank")
    else:
        raise ValueError("Unknown strategy")
    build_ms = round((time.perf_counter() - started) * 1000, 3)
    def run(question: dict, phase: str, iteration: int) -> dict:
        begin = time.perf_counter()
        try:
            hits = engine.search(question["question"], k)
            return {"question_id": question["question_id"], "phase": phase, "iteration": iteration,
                    "elapsed_ms": round((time.perf_counter() - begin) * 1000, 3),
                    "hit_count": len(hits), "error": None}
        except Exception as exc:
            return {"question_id": question["question_id"], "phase": phase, "iteration": iteration,
                    "elapsed_ms": round((time.perf_counter() - begin) * 1000, 3),
                    "hit_count": 0, "error": type(exc).__name__}
    cold = [run(question, "first_query", 0) for question in questions]
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        warm = list(pool.map(lambda item: run(item[0], "warm", item[1]),
                             [(question, iteration) for iteration in range(1, repeat + 1) for question in questions]))
    rows = cold + warm
    def summary(phase: str) -> dict:
        timings = [row["elapsed_ms"] for row in rows if row["phase"] == phase and row["error"] is None]
        return {"n": len(timings), "p50_ms": _percentile(timings, .5) if timings else None,
                "p95_ms": _percentile(timings, .95) if timings else None,
                "mean_ms": round(statistics.mean(timings), 3) if timings else None}
    return {"mode": "retrieval_only", "strategy": strategy, "build_ms": build_ms,
            "first_query": summary("first_query"), "warm": summary("warm"),
            "questions": len(questions), "repeat": repeat, "concurrency": concurrency, "k": k,
            "errors": sum(row["error"] is not None for row in rows), "calls": len(rows),
            "questions_sha256": digest(questions_path.read_bytes()),
            "passages_sha256": digest(passages_path.read_bytes()),
            "platform": {"python": platform.python_version(), "machine": platform.machine(),
                         "system": platform.system()}, "observations": rows}


def measure_generation_variability(questions_path: Path, passages_path: Path, corpus_manifest: dict,
                                   selected_ids: list[str], generator: LocalGenerator | None = None,
                                   repeats: int = 3) -> dict:
    if repeats != 3 or not selected_ids or len(selected_ids) != len(set(selected_ids)) or len(selected_ids) > 10:
        raise ValueError("Select 1–10 distinct development questions and exactly three repetitions")
    questions = {q["question_id"]: q for q in read_jsonl(questions_path) if q.get("split") == "dev"}
    if not set(selected_ids) <= set(questions):
        raise ValueError("Selected IDs must belong to development questions")
    passages = read_jsonl(passages_path)
    engine = BM25(passages)
    model = generator or LocalGenerator()
    rows = []
    for qid in selected_ids:
        question = questions[qid]["question"]
        context = pack(engine.search(question, 5), 7000)
        if not context:
            raise ValueError(f"No model context for {qid}")
        for iteration in range(1, repeats + 1):
            started = time.perf_counter()
            try:
                answer = model.generate(question, context, corpus_manifest)
                error = None
            except Exception as exc:
                answer, error = None, type(exc).__name__
            rows.append({"question_id": qid, "iteration": iteration,
                         "context_passage_ids": [p["passage_id"] for p in context],
                         "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                         "status": answer.get("status") if answer else None,
                         "answer_sha256": digest(json.dumps({key: answer.get(key) for key in
                             ("status", "claims", "limitations", "clarification_question", "sources")},
                             sort_keys=True, ensure_ascii=False)) if answer else None,
                         "usage": answer.get("usage") if answer else None, "error": error})
    variation = {qid: {"distinct_answer_hashes": len({row["answer_sha256"] for row in rows
                                                      if row["question_id"] == qid and row["answer_sha256"]}),
                       "errors": sum(row["error"] is not None for row in rows if row["question_id"] == qid)}
                 for qid in selected_ids}
    timings = [row["elapsed_ms"] for row in rows if row["error"] is None]
    token_totals = {key: sum(row["usage"].get(key, 0) for row in rows
                             if isinstance(row.get("usage"), dict) and isinstance(row["usage"].get(key), int))
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return {"mode": "generation_variability_dev", "model": model.model,
            "questions_sha256": digest(questions_path.read_bytes()),
            "passages_sha256": digest(passages_path.read_bytes()),
            "selected_ids": selected_ids, "repeats": repeats, "calls": len(rows),
            "errors": sum(row["error"] is not None for row in rows),
            "latency_p50_ms": _percentile(timings, .5) if timings else None,
            "latency_p95_ms": _percentile(timings, .95) if timings else None,
            "token_totals": token_totals, "variation": variation, "observations": rows}
