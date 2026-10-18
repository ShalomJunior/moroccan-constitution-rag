"""Release and reserved-test preflight; no test output is opened for selection."""
import json
import subprocess
import time
from pathlib import Path
from .store import ROOT, digest, read_jsonl, write_jsonl
from .evidence import validate_answer

EXPECTED_FAMILIES = {"dev": 45, "validation": 45, "test": 90}
FINAL_SYSTEMS = ("fulltext", "bm25_rag", "selected_pipeline")


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError as exc:
        raise ValueError("Release inputs must be inside the repository") from exc


def release_readiness(questions_path: Path, corpus_manifest_path: Path,
                      selection_path: Path, systems_path: Path,
                      analysis_plan_path: Path | None = None, repo_root: Path = ROOT) -> dict:
    analysis_plan_path = analysis_plan_path or repo_root / "configs/analysis_plan.json"
    reasons = []
    corpus = json.loads(corpus_manifest_path.read_text())
    questions = read_jsonl(questions_path) if questions_path.exists() else []
    if corpus.get("review_status") != "reviewed":
        reasons.append("Corpus is not reviewed")
    counts = {}
    seen = {}
    for split in EXPECTED_FAMILIES:
        subset = [q for q in questions if q.get("split") == split]
        counts[split] = len({q.get("family_id") for q in subset})
        if counts[split] != EXPECTED_FAMILIES[split]:
            reasons.append(f"{split} needs {EXPECTED_FAMILIES[split]} families")
        if any(q.get("review_status") != "reviewed" or q.get("corpus_hash") != corpus.get("corpus_hash") for q in subset):
            reasons.append(f"{split} labels are not all reviewed against this corpus")
        if any(q.get("expected_status") not in {"answered", "partially_answered", "needs_clarification",
                                                   "insufficient_evidence", "out_of_scope"} for q in subset):
            reasons.append(f"{split} has missing expected statuses")
        if any(not q.get("acceptable_evidence_sets") for q in subset
               if q.get("expected_status") in {"answered", "partially_answered"}):
            reasons.append(f"{split} answerable questions have missing sufficient evidence labels")
        for q in subset:
            family = q.get("family_id")
            if family in seen and seen[family] != split:
                reasons.append(f"Family {family} crosses splits")
            seen[family] = split
    if not questions:
        reasons.append("Reviewed question file is missing")
    if any(q.get("split") not in EXPECTED_FAMILIES or q.get("language") != "fr" for q in questions):
        reasons.append("Question file contains an unexpected split or language")
    selection = json.loads(selection_path.read_text()) if selection_path.exists() else {}
    if selection.get("status") != "ready_for_retrieval_selection" or not selection.get("selected_retrieval_run"):
        reasons.append("Validated retrieval selection is missing")
    elif selection.get("questions_sha256") != digest(questions_path.read_bytes()):
        reasons.append("Selection does not match the frozen questions")
    systems = json.loads(systems_path.read_text()) if systems_path.exists() else {}
    if set(systems) != set(FINAL_SYSTEMS):
        reasons.append("Three final system configurations are not fixed")
    elif any(not systems[name].get("model") or not systems[name].get("prompt_sha256") for name in FINAL_SYSTEMS):
        reasons.append("Final model or prompt hashes are missing")
    elif systems["fulltext"].get("context_mode") != "fulltext" or systems["bm25_rag"].get("strategy") != "bm25":
        reasons.append("Full-text and BM25 baselines are not defined as planned")
    else:
        from .campaign import prompt_hash
        if len({systems[name].get("model") for name in FINAL_SYSTEMS}) != 1 or any(
                systems[name].get("prompt_sha256") != prompt_hash() for name in FINAL_SYSTEMS):
            reasons.append("Final systems must use one model and the current Qwen prompt")
    if not analysis_plan_path.exists():
        reasons.append("Analysis plan is missing")
    lock_path = repo_root / "uv.lock"
    if not lock_path.exists():
        reasons.append("Dependency lock is missing")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True,
                                         stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root, text=True,
                                             stderr=subprocess.DEVNULL).strip())
        if dirty:
            reasons.append("Working tree is not clean")
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
        reasons.append("Git revision is unavailable")
    return {"status": "ready" if not reasons else "blocked", "reasons": list(dict.fromkeys(reasons)),
            "commit": commit, "dirty": dirty,
            "corpus_hash": corpus.get("corpus_hash"),
            "questions_sha256": digest(questions_path.read_bytes()) if questions_path.exists() else None,
            "selection_sha256": digest(selection_path.read_bytes()) if selection_path.exists() else None,
            "selection_path": _repo_relative(selection_path, repo_root),
            "systems_sha256": digest(systems_path.read_bytes()) if systems_path.exists() else None,
            "systems_path": _repo_relative(systems_path, repo_root),
            "analysis_plan_sha256": digest(analysis_plan_path.read_bytes()) if analysis_plan_path.exists() else None,
            "analysis_plan_path": _repo_relative(analysis_plan_path, repo_root),
            "lock_sha256": digest(lock_path.read_bytes()) if lock_path.exists() else None,
            "family_counts": counts}


def assert_reserved_test_ready(release_manifest_path: Path, questions_path: Path,
                               corpus_manifest_path: Path) -> dict:
    frozen = json.loads(release_manifest_path.read_text())
    if frozen.get("status") != "ready":
        raise ValueError("Reserved test requires a ready release manifest")
    if frozen.get("questions_sha256") != digest(questions_path.read_bytes()):
        raise ValueError("Reserved questions changed after release freeze")
    corpus = json.loads(corpus_manifest_path.read_text())
    if corpus.get("review_status") != "reviewed" or frozen.get("corpus_hash") != corpus.get("corpus_hash"):
        raise ValueError("Reserved corpus changed after release freeze")
    for name in ("selection", "systems", "analysis_plan"):
        relative = Path(frozen.get(name + "_path", ""))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Reserved {name} path is invalid")
        path = ROOT / relative
        if not path.is_file() or digest(path.read_bytes()) != frozen.get(name + "_sha256"):
            raise ValueError(f"Reserved {name} changed after release freeze")
    lock_path = ROOT / "uv.lock"
    if not lock_path.exists() or digest(lock_path.read_bytes()) != frozen.get("lock_sha256"):
        raise ValueError("Dependency lock changed after release freeze")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                     stderr=subprocess.DEVNULL).strip()
    if commit != frozen.get("commit"):
        raise ValueError("Code revision changed after release freeze")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                               stderr=subprocess.DEVNULL).strip():
        raise ValueError("Working tree changed after release freeze")
    return frozen


def run_reserved_test(release_manifest_path: Path, questions_path: Path, corpus_manifest_path: Path,
                      output_dir: Path, runners: dict, expected_families: int = 90) -> dict:
    """Execute fixed system adapters once per question, saving each result atomically."""
    frozen = assert_reserved_test_ready(release_manifest_path, questions_path, corpus_manifest_path)
    if set(runners) != set(FINAL_SYSTEMS):
        raise ValueError("Reserved test needs exactly the three frozen systems")
    questions = [q for q in read_jsonl(questions_path) if q.get("split") == "test"]
    if len({q["family_id"] for q in questions}) != expected_families or len({q["question_id"] for q in questions}) != len(questions):
        raise ValueError("Reserved test question inventory is incomplete")
    if any(q.get("review_status") != "reviewed" for q in questions):
        raise ValueError("Reserved test questions are not reviewed")
    corpus = json.loads(corpus_manifest_path.read_text())
    passages_path = corpus_manifest_path.parent / "passages.jsonl"
    if digest(passages_path.read_bytes()) != corpus["passages_hash"]:
        raise ValueError("Reserved passages changed after release freeze")
    passages = {row["passage_id"]: row for row in read_jsonl(passages_path)}
    expected = {"release_sha256": digest(release_manifest_path.read_bytes()),
                "questions_sha256": digest(questions_path.read_bytes()),
                "question_ids": [q["question_id"] for q in questions],
                "systems": list(FINAL_SYSTEMS)}
    output_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = output_dir / "manifest.json"
    if run_manifest.exists():
        if json.loads(run_manifest.read_text()) != expected:
            raise ValueError("Reserved run ID belongs to different inputs")
    else:
        if any((output_dir / system / "answers.jsonl").exists() for system in FINAL_SYSTEMS):
            raise ValueError("Reserved answers exist without a manifest")
        run_manifest.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n")
    summary = {}
    for system in FINAL_SYSTEMS:
        path = output_dir / system / "answers.jsonl"
        rows = read_jsonl(path) if path.exists() else []
        done = {row["question_id"]: row for row in rows}
        if len(done) != len(rows) or not set(done) <= set(expected["question_ids"]):
            raise ValueError(f"{system} has duplicate or unknown question IDs")
        for question in questions:
            qid = question["question_id"]
            if qid in done:
                continue
            started = time.perf_counter()
            try:
                result = runners[system](question["question"])
                if not isinstance(result, dict) or not isinstance(result.get("answer"), dict):
                    raise ValueError("Runner must return an answer and context trace")
                answer, context_ids, error = result["answer"], result.get("context_passage_ids", []), None
                if not isinstance(context_ids, list) or any(pid not in passages for pid in context_ids):
                    raise ValueError("Runner context IDs do not match the frozen passages")
                supplied = [passages[pid] for pid in context_ids]
                validate_answer(answer, supplied)
                if any(source.get("passage_id") not in set(context_ids) for source in answer.get("sources", [])):
                    raise ValueError("Answer source was not in the supplied context")
            except Exception as exc:
                answer, context_ids = None, []
                error = {"type": type(exc).__name__, "message": str(exc)}
            done[qid] = {"question_id": qid, "family_id": question["family_id"],
                         "answer": answer, "context_passage_ids": context_ids,
                         "error": error, "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}
            write_jsonl(path, [done[item] for item in expected["question_ids"] if item in done])
        summary[system] = {"completed": len(done), "errors": sum(row["error"] is not None for row in done.values()),
                           "answers_path": str(path)}
    return {"status": "complete", "systems": summary, "questions": len(questions),
            "run_manifest_sha256": digest(run_manifest.read_bytes())}
