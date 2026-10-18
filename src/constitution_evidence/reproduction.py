"""Offline verification of saved retrieval results and publishable repository files."""
import json
import re
import subprocess
from pathlib import Path
from .evaluation import score_retrieval, report
from .store import ROOT, digest, read_jsonl


def reproduce_retrieval(questions_path: Path, passages_path: Path, run_dirs: list[Path]) -> dict:
    if not run_dirs:
        raise ValueError("At least one saved run is required")
    questions = {q["question_id"]: q for q in read_jsonl(questions_path)}
    passages = {p["passage_id"]: p for p in read_jsonl(passages_path)}
    output = {}
    for run_dir in run_dirs:
        manifest = json.loads((run_dir / "manifest.json").read_text())
        if manifest.get("questions_sha256") != digest(questions_path.read_bytes()) or manifest.get("passages_sha256") != digest(passages_path.read_bytes()):
            raise ValueError(f"Saved run inputs changed: {run_dir}")
        rows = read_jsonl(run_dir / "retrieval.jsonl")
        expected_ids = manifest["question_ids"]
        if len(rows) != len(expected_ids) or {row["question_id"] for row in rows} != set(expected_ids):
            raise ValueError(f"Saved run is incomplete: {run_dir}")
        for row in rows:
            q = questions[row["question_id"]]
            if q.get("split") != manifest["split"] or q.get("family_id") != row["family_id"]:
                raise ValueError("Saved question identity changed")
            try:
                hits = [{**passages[item["passage_id"]], "score": item.get("score")}
                        for item in row["hits"]]
                context = [passages[pid] for pid in row["context_passage_ids"]]
            except KeyError as exc:
                raise ValueError("Saved run references an unknown passage") from exc
            actual = score_retrieval(hits, q.get("relevant_articles", []), manifest["article_k"],
                                     q.get("acceptable_evidence_sets"), q.get("relevant_spans"), context)
            if actual != row["metrics"]:
                raise ValueError(f"Saved metrics do not match hits and labels: {row['question_id']}")
        output[run_dir.name] = report(run_dir)
    return {"mode": "offline_reproduction", "questions_sha256": digest(questions_path.read_bytes()),
            "passages_sha256": digest(passages_path.read_bytes()), "runs": output}


def publication_audit(root: Path = ROOT) -> dict:
    """Inspect Git-tracked payloads; never scan ignored local secrets or downloads."""
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    tracked = [Path(item) for item in tracked if item]
    findings = []
    forbidden_exact = {".env", "PROJECT_LOG.md", "data/annotations/test-candidates.jsonl",
                       "docs/demo-script.md", "docs/experiments.md", "docs/release-and-judgments.md",
                       "docs/v2-decision-gate.md", "reports/technical-report.md",
                       "reports/installation-and-usability.md"}
    forbidden_prefix = ("data/raw/", "data/ocr/", "data/processed/", "data/models/", "runs/",
                        "constitution-rag/")
    secret = re.compile(rb"(?:AIza[0-9A-Za-z_-]{30,}|(?:gsk_|ghp_|github_pat_)[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{20,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)")
    for relative in tracked:
        name = relative.as_posix()
        if name in forbidden_exact or any(name.startswith(prefix) for prefix in forbidden_prefix):
            findings.append({"path": name, "issue": "nonpublishable generated or private file is tracked"})
            continue
        path = root / relative
        if not path.is_file():
            continue
        if path.stat().st_size > 5_000_000:
            findings.append({"path": name, "issue": "tracked file exceeds 5 MB; review redistribution"})
            continue
        if secret.search(path.read_bytes()):
            findings.append({"path": name, "issue": "possible credential pattern in tracked file"})
    return {"status": "pass" if not findings else "review_required", "tracked_files": len(tracked),
            "findings": findings}
