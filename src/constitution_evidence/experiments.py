"""Compare saved retrieval runs and prepare reviewed oracle contexts."""
import json
import time
from pathlib import Path
from .store import digest, read_jsonl, write_jsonl
from .local_generation import LOCAL_PROMPT_VERSION, RAW_SCHEMA, LocalGenerator
from .generation import INSTRUCTIONS


def _run(path: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((path / "manifest.json").read_text())
    rows = read_jsonl(path / "retrieval.jsonl")
    expected = manifest["question_ids"]
    if len(rows) != manifest["question_count"] or len(expected) != len(rows):
        raise ValueError("Run is incomplete")
    by_id = {row["question_id"]: row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != set(expected):
        raise ValueError("Run has missing or duplicate question IDs")
    return manifest, [by_id[qid] for qid in expected]


def compare_runs(left: Path, right: Path) -> dict:
    """Paired article/evidence comparison; refuse mismatched data or test splits."""
    a, left_rows = _run(left)
    b, right_rows = _run(right)
    if a["split"] == "test" or b["split"] == "test":
        raise ValueError("Test runs are reserved for final evaluation")
    keys = ("split", "article_k", "context_chars", "question_ids", "questions_sha256",
            "passages_sha256", "evaluation_code_sha256")
    if any(a.get(key) != b.get(key) for key in keys):
        raise ValueError("Runs must share split, questions, corpus, k, and context budget")
    details = []
    for one, two in zip(left_rows, right_rows):
        if one["family_id"] != two["family_id"]:
            raise ValueError("Family IDs differ")
        metrics = {}
        for key in ("recall", "mrr", "complete_evidence", "context_evidence_coverage"):
            x, y = one["metrics"].get(key), two["metrics"].get(key)
            metrics[key] = None if x is None or y is None else round(y - x, 6)
        details.append({"question_id": one["question_id"], "family_id": one["family_id"], "delta": metrics})
    averages = {}
    for key in ("recall", "mrr", "complete_evidence", "context_evidence_coverage"):
        values = [row["delta"][key] for row in details if row["delta"][key] is not None]
        averages[key] = {"mean_delta": round(sum(values) / len(values), 6) if values else None, "n": len(values)}
    return {"left": str(left), "right": str(right), "split": a["split"],
            "left_method": a["method"], "right_method": b["method"],
            "questions_sha256": a["questions_sha256"], "passages_sha256": a["passages_sha256"],
            "metrics": averages, "per_question": details}


def validate_selection_inputs(questions_path: Path, run_paths: list[Path], minimum_families: int = 45) -> dict:
    """Preflight for selection; never treat provisional labels as validation."""
    questions = read_jsonl(questions_path)
    validation = [q for q in questions if q.get("split") == "validation"]
    families = {q.get("family_id") for q in validation}
    if any(q.get("family_id") in families for q in questions if q.get("split") != "validation"):
        raise ValueError("A validation family crosses splits")
    if len(families) < minimum_families:
        raise ValueError(f"Validation needs at least {minimum_families} distinct families")
    if any(q.get("review_status") != "reviewed" for q in validation):
        raise ValueError("Validation questions are not all reviewed")
    if any(q.get("expected_status") not in {"answered", "partially_answered", "needs_clarification",
                                               "insufficient_evidence", "out_of_scope"} for q in validation):
        raise ValueError("Validation questions need expected answer statuses")
    answerable = {q["question_id"] for q in validation
                  if q["expected_status"] in {"answered", "partially_answered"}}
    if not answerable or any(not q.get("acceptable_evidence_sets") for q in validation if q["question_id"] in answerable):
        raise ValueError("Answerable validation questions need reviewed sufficient evidence sets")
    if not run_paths:
        raise ValueError("At least one candidate run is required")
    manifests = []
    for path in run_paths:
        manifest, rows = _run(path)
        if manifest["split"] != "validation" or manifest["questions_sha256"] != digest(questions_path.read_bytes()):
            raise ValueError("Candidate run does not match the validation questions")
        if set(manifest["question_ids"]) != {q["question_id"] for q in validation}:
            raise ValueError("Candidate run omits validation questions")
        if any(row["metrics"].get("complete_evidence") is None for row in rows
               if row["question_id"] in answerable):
            raise ValueError("Candidate run lacks evidence coverage for answerable questions")
        manifests.append(manifest)
    if len({m["passages_sha256"] for m in manifests}) != 1 or len({m["article_k"] for m in manifests}) != 1:
        raise ValueError("Candidates must use the same corpus and k")
    return {"status": "ready_for_retrieval_selection", "family_count": len(families),
            "candidate_count": len(manifests), "answerable_questions": len(answerable),
            "questions_sha256": digest(questions_path.read_bytes())}


def select_validation(questions_path: Path, run_paths: list[Path], policy_path: Path) -> dict:
    policy = json.loads(policy_path.read_text())
    if policy.get("primary_metric") != "complete_evidence" or policy.get("tie_breaker") != "mrr":
        raise ValueError("Unknown validation selection policy")
    readiness = validate_selection_inputs(questions_path, run_paths, policy.get("minimum_families", 45))
    answerable = {q["question_id"] for q in read_jsonl(questions_path)
                  if q.get("split") == "validation" and q.get("expected_status") in {"answered", "partially_answered"}}
    candidates = []
    for path in run_paths:
        manifest, rows = _run(path)
        evidence = [row["metrics"]["complete_evidence"] for row in rows if row["question_id"] in answerable]
        mrr = [row["metrics"]["mrr"] for row in rows
               if row["question_id"] in answerable and row["metrics"]["mrr"] is not None]
        candidates.append({"run": path.name, "method": manifest["method"],
                           "complete_evidence": sum(evidence) / len(evidence),
                           "mrr": sum(mrr) / len(mrr) if mrr else None})
    ranked = sorted(candidates, key=lambda item: (-item["complete_evidence"],
                                                    -(item["mrr"] if item["mrr"] is not None else -1), item["run"]))
    return {**readiness, "policy_sha256": digest(policy_path.read_bytes()),
            "selected_retrieval_run": ranked[0]["run"], "candidates": ranked,
            "note": "Generation, answer risk, and abstention threshold require separately reviewed response judgments."}


def oracle_context(question: dict, passages: list[dict], corpus_hash: str) -> list[dict]:
    """Return only reviewed source passages, never answer labels or required claims."""
    if question.get("split") not in {"dev", "validation"}:
        raise ValueError("Oracle context is limited to dev and validation")
    if question.get("review_status") != "reviewed" or question.get("corpus_hash") != corpus_hash:
        raise ValueError("Oracle requires reviewed, corpus-matched annotations")
    groups = question.get("acceptable_evidence_sets")
    if not groups or any(not group for group in groups):
        raise ValueError("Oracle requires sufficient evidence spans")
    by_id = {passage["passage_id"]: passage for passage in passages}
    selected = []
    for span in groups[0]:
        passage = by_id.get(span["passage_id"])
        if passage is None or not 0 <= span["char_start"] < span["char_end"] <= len(passage["canonical_text"]):
            raise ValueError("Oracle span does not match the current corpus")
        if passage not in selected:
            selected.append(passage)
    return selected


def run_oracle(questions_path: Path, passages_path: Path, corpus_manifest: dict,
               output_dir: Path, split: str, generator: LocalGenerator | None = None) -> dict:
    if split not in {"dev", "validation"}:
        raise ValueError("Oracle runs are limited to dev and validation")
    if corpus_manifest.get("review_status") != "reviewed":
        raise ValueError("Oracle requires a reviewed corpus")
    questions = [q for q in read_jsonl(questions_path) if q.get("split") == split]
    if not questions or len({q["question_id"] for q in questions}) != len(questions):
        raise ValueError("Oracle needs distinct questions")
    passages = read_jsonl(passages_path)
    if corpus_manifest.get("passages_hash") and digest(passages_path.read_bytes()) != corpus_manifest["passages_hash"]:
        raise ValueError("Oracle passages do not match the active corpus manifest")
    contexts = {q["question_id"]: oracle_context(q, passages, corpus_manifest["corpus_hash"]) for q in questions}
    model = generator or LocalGenerator()
    expected = {"mode": "oracle_diagnostic", "split": split, "question_ids": [q["question_id"] for q in questions],
                "questions_sha256": digest(questions_path.read_bytes()),
                "passages_sha256": digest(passages_path.read_bytes()),
                "corpus_hash": corpus_manifest["corpus_hash"], "model": model.model,
                "prompt_version": LOCAL_PROMPT_VERSION,
                "prompt_sha256": digest(INSTRUCTIONS + LOCAL_PROMPT_VERSION + json.dumps(RAW_SCHEMA, sort_keys=True))}
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path, rows_path = output_dir / "manifest.json", output_dir / "oracle.jsonl"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text()) != expected:
            raise ValueError("Oracle run inputs or model changed")
    elif rows_path.exists():
        raise ValueError("Oracle rows exist without a manifest")
    else:
        manifest_path.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n")
    rows = read_jsonl(rows_path) if rows_path.exists() else []
    done = {row["question_id"]: row for row in rows}
    if len(done) != len(rows) or not set(done) <= set(expected["question_ids"]):
        raise ValueError("Oracle rows contain duplicates or unknown IDs")
    for question in questions:
        qid = question["question_id"]
        if qid in done:
            continue
        context = contexts[qid]
        started = time.perf_counter()
        try:
            answer = model.generate(question["question"], context, corpus_manifest)
            error = None
        except Exception as exc:
            answer, error = None, {"type": type(exc).__name__, "message": str(exc)}
        done[qid] = {"question_id": qid, "family_id": question["family_id"],
                     "context_passage_ids": [p["passage_id"] for p in context],
                     "answer": answer, "error": error,
                     "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}
        write_jsonl(rows_path, [done[item] for item in expected["question_ids"] if item in done])
    return {"mode": "oracle_diagnostic", "questions": len(questions),
            "completed": len(done), "errors": sum(row["error"] is not None for row in done.values()),
            "output_dir": str(output_dir)}
