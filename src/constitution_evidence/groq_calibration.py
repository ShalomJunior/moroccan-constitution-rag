"""Resumable, development-only Groq calibration over the active corpus."""
import json
import time
from collections import Counter
from pathlib import Path

from . import evidence, generation, groq_generation, local_generation, retrieval
from .evidence import pack_with_article_leads
from .generation import GenerationError
from .groq_generation import GROQ_PROMPT_VERSION, GroqGenerator
from .retrieval import BM25
from .store import digest, read_jsonl, write_jsonl


def run_calibration(questions_path: Path, passages_path: Path, corpus_manifest_path: Path,
                    output_dir: Path, generator: GroqGenerator | None = None,
                    max_new: int = 15, pause_seconds: float = 18.0) -> dict:
    if not 1 <= max_new <= 15 or not 0 <= pause_seconds <= 60:
        raise ValueError("Calibration allows 1–15 new questions and a 0–60 second pause")
    questions = [q for q in read_jsonl(questions_path) if q.get("split") == "dev"]
    if not questions or len(questions) > 15 or len({q["question_id"] for q in questions}) != len(questions):
        raise ValueError("Calibration requires 1–15 unique development questions")
    passages = read_jsonl(passages_path)
    corpus_manifest = json.loads(corpus_manifest_path.read_text(encoding="utf-8"))
    if digest(passages_path.read_bytes()) != corpus_manifest["passages_hash"]:
        raise ValueError("Passages differ from the active corpus manifest")
    model = generator or GroqGenerator()
    expected = {
        "status": "provisional_generation_calibration", "split": "dev", "strategy": "bm25",
        "top_k": 5, "context_chars": 7000, "context_policy": "ranked_hits_plus_adjacent_paragraphs_v2",
        "question_ids": [q["question_id"] for q in questions],
        "questions_sha256": digest(questions_path.read_bytes()),
        "corpus_hash": corpus_manifest["corpus_hash"],
        "passages_hash": corpus_manifest["passages_hash"],
        "model": model.model, "model_revision": None,
        "prompt_version": GROQ_PROMPT_VERSION,
        "generator_code_sha256": digest(Path(groq_generation.__file__).read_bytes()),
        "prompt_code_sha256": digest(Path(generation.__file__).read_bytes()),
        "retrieval_code_sha256": digest(Path(retrieval.__file__).read_bytes()),
        "validation_code_sha256": digest(Path(local_generation.__file__).read_bytes()),
        "evidence_code_sha256": digest(Path(evidence.__file__).read_bytes())}
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path, rows_path = output_dir / "manifest.json", output_dir / "responses.jsonl"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != expected:
            raise ValueError("Run ID belongs to different inputs or code")
    elif rows_path.exists():
        raise ValueError("Run responses exist without a manifest")
    else:
        manifest_path.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = read_jsonl(rows_path) if rows_path.exists() else []
    done = {row["question_id"] for row in rows}
    if len(done) != len(rows) or not done <= set(expected["question_ids"]):
        raise ValueError("Existing responses have duplicate or unknown question IDs")
    remaining = [q for q in questions if q["question_id"] not in done][:max_new]
    engine = BM25(passages) if remaining else None
    for index, question in enumerate(remaining):
        if index:
            time.sleep(pause_seconds)
        context = pack_with_article_leads(engine.search(question["question"], 5), passages, 7000)
        row = {"question_id": question["question_id"],
               "context_passage_ids": [p["passage_id"] for p in context],
               "context_text_hashes": [p["text_hash"] for p in context]}
        started = time.perf_counter()
        if context:
            try:
                row["answer"] = model.generate(question["question"], context, corpus_manifest)
                row["error"] = None
            except GenerationError as exc:
                row["answer"] = None
                row["error"] = str(exc)
        else:
            row["answer"], row["error"] = None, "no_context"
        row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        rows.append(row)
        write_jsonl(rows_path, rows)
        print(f"Saved {len(rows)}/{len(questions)} {question['question_id']} ({'error' if row['error'] else 'ok'})", flush=True)
    statuses = Counter(row["answer"]["status"] for row in rows if row.get("answer"))
    errors = Counter(row["error"] for row in rows if row.get("error"))
    tokens = {key: sum((row.get("answer") or {}).get("usage", {}).get(key, 0)
                       for row in rows if isinstance((row.get("answer") or {}).get("usage"), dict))
              for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return {"run_dir": str(output_dir), "questions": len(questions), "saved": len(rows),
            "complete": len(rows) == len(questions), "statuses": dict(statuses),
            "errors": dict(errors), "token_totals": tokens,
            "corpus_hash": corpus_manifest["corpus_hash"], "model": model.model}
