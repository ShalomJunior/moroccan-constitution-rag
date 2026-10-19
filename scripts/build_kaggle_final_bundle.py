"""Package a clean release checkout and private, frozen inputs for Kaggle."""
import argparse
import base64
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

from constitution_evidence.release import assert_reserved_test_ready, release_readiness
from constitution_evidence.reproduction import reproduce_retrieval
from constitution_evidence.store import ROOT


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path, previous_results: Path | None = None) -> dict:
    questions = ROOT / "runs/complete-owner-reviewed-benchmark.jsonl"
    release = ROOT / "runs/release-candidate/manifest.json"
    frozen = assert_reserved_test_ready(release, questions, ROOT / "data/processed/manifest.json")
    if git("status", "--porcelain"):
        raise ValueError("Build from a clean checkout")
    commit = git("rev-parse", "HEAD")
    if commit != frozen["commit"]:
        raise ValueError("Release manifest belongs to another commit")
    selection = json.loads((ROOT / "runs/validation-selection.json").read_text())
    run_ids = [candidate["run"] for candidate in selection["candidates"]]
    if selection["selected_retrieval_run"] not in run_ids or len(run_ids) != len(set(run_ids)):
        raise ValueError("Validation selection has duplicate or missing candidate runs")
    private_files = [
        "data/processed/manifest.json", "data/processed/articles.jsonl",
        "data/processed/passages.jsonl", "runs/complete-owner-reviewed-benchmark.jsonl",
        "runs/validation-selection.json", "runs/release-candidate/manifest.json",
    ]
    for run_id in run_ids:
        if not run_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid validation run ID")
        private_files.extend([f"runs/{run_id}/manifest.json", f"runs/{run_id}/retrieval.jsonl"])
    for name in private_files:
        if not (ROOT / name).is_file():
            raise FileNotFoundError(ROOT / name)
    readiness = release_readiness(
        questions, ROOT / "data/processed/manifest.json",
        ROOT / "runs/validation-selection.json", ROOT / "configs/final_systems.json")
    if readiness["status"] != "ready":
        raise ValueError(f"Release gate blocked: {readiness['reasons']}")
    reproduce_retrieval(
        questions, ROOT / "data/processed/passages.jsonl",
        [ROOT / "runs" / run_id for run_id in run_ids])
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(prefix="constitution-final-") as directory:
        checkout = Path(directory) / "checkout"
        branch = git("branch", "--show-current")
        subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", branch,
                        ROOT.as_uri(), str(checkout)], check=True)
        if git("rev-parse", "HEAD", cwd=checkout) != commit:
            raise ValueError("Bundle checkout differs from the release commit")
        git("remote", "set-url", "origin", git("remote", "get-url", "origin"), cwd=checkout)
        for name in private_files:
            destination = checkout / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        if previous_results is not None:
            previous_root = checkout / "runs/previous-final-results"
            expected = {f"runs/final-reserved-qwen4b-transformers/{name}"
                        for name in ("manifest.json", "model-provenance.json",
                                     "bm25_rag/answers.jsonl", "selected_pipeline/answers.jsonl")}
            expected.add("runs/release-candidate/manifest.json")
            with zipfile.ZipFile(previous_results) as source:
                found = set(source.namelist())
                if not expected <= found:
                    raise ValueError(f"Previous results lack required files: {sorted(expected - found)}")
                allowed = expected | {"runs/final-reserved-qwen4b-transformers/fulltext/answers.jsonl"}
                if found != allowed:
                    raise ValueError("Previous results have unexpected files")
                for name in sorted(found):
                    destination = previous_root / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(source.read(name))
                    private_files.append(destination.relative_to(checkout).as_posix())
            source_hash = previous_root / "source-archive-sha256.txt"
            source_hash.write_text(sha256(previous_results) + "\n")
            private_files.append(source_hash.relative_to(checkout).as_posix())
            from scripts.kaggle_final_runtime import seed_previous_results
            with tempfile.TemporaryDirectory(prefix="constitution-recovery-check-") as check_dir:
                seed_previous_results(checkout, Path(check_dir) / "run")
        git_buffer = io.BytesIO()
        with tarfile.open(fileobj=git_buffer, mode="w:gz") as archive:
            archive.add(checkout / ".git", arcname=".git", recursive=True)
        git_metadata = git_buffer.getvalue()
        marker = {"commit": commit, "release_sha256": sha256(release),
                  "questions_sha256": sha256(questions),
                  "files": {name: sha256(checkout / name) for name in private_files},
                  "git_metadata_sha256": hashlib.sha256(git_metadata).hexdigest(),
                  "git_metadata_b64": base64.b64encode(git_metadata).decode("ascii")}
        marker_path = checkout / "runs/kaggle-bundle.json"
        marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n")
        if git("status", "--porcelain", cwd=checkout):
            raise ValueError("Private bundle files are not ignored by Git")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(checkout.rglob("*")):
                if path.is_file() and ".git" not in path.relative_to(checkout).parts:
                    archive.write(path, path.relative_to(checkout).as_posix())
            archive.comment = commit.encode("ascii")
    return {"archive": str(output), "commit": commit, "sha256": sha256(output),
            "private_files": len(private_files)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "runs/constitution-evidence-final-input.zip")
    parser.add_argument("--previous-results", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.previous_results), ensure_ascii=False, indent=2))
