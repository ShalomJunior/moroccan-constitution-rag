import base64
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.kaggle_bundle_loader import restore_git_metadata
from scripts.build_kaggle_final_bundle import previous_result_members


def make_bundle(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    (source / "README.md").write_text(f"sample-{tmp_path.name}\n")
    subprocess.run(["git", "add", "README.md"], cwd=source, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                    "commit", "-qm", "sample"], cwd=source, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        archive.add(source / ".git", arcname=".git")
    metadata = buffer.getvalue()
    runs = source / "runs"
    runs.mkdir()
    (runs / "kaggle-bundle.json").write_text(json.dumps({
        "commit": commit,
        "git_metadata_b64": base64.b64encode(metadata).decode(),
        "git_metadata_sha256": hashlib.sha256(metadata).hexdigest(),
    }))
    shutil.rmtree(source / ".git")
    archive_path = tmp_path / "constitution-evidence-final-input.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in source.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(source))
    return archive_path


def check_first_cell(tmp_path, extracted):
    archive_path = make_bundle(tmp_path)
    input_root = tmp_path / "input"
    input_root.mkdir()
    if extracted:
        folder = input_root / "dataset"
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(folder)
    else:
        shutil.copy2(archive_path, input_root / archive_path.name)
    working_root = tmp_path / "working" / "moroccan-constitution-rag"
    working_root.mkdir(parents=True)
    # An interrupted first cell must repair the existing working directory.
    notebook = json.loads(Path("notebooks/kaggle_final.ipynb").read_text())
    cell = "".join(notebook["cells"][1]["source"])
    cell = cell.replace("/kaggle/input", str(input_root))
    cell = cell.replace("/kaggle/working/moroccan-constitution-rag", str(working_root))
    exec(compile(cell, "kaggle_final_first_cell", "exec"), {})
    exec(compile(cell, "kaggle_final_first_cell", "exec"), {})
    assert (working_root / ".git").is_dir()
    assert restore_git_metadata(working_root) == json.loads(
        (working_root / "runs/kaggle-bundle.json").read_text())["commit"]


class KaggleBundleLoaderTests(unittest.TestCase):
    def test_zip_and_kaggle_extracted_folder(self):
        for extracted in (False, True):
            with self.subTest(extracted=extracted), tempfile.TemporaryDirectory() as directory:
                check_first_cell(Path(directory), extracted)

    def test_recovery_archive_accepts_optional_fulltext_and_lineage(self):
        base = "runs/final-reserved-qwen4b-transformers/"
        required = [base + name for name in ("manifest.json", "model-provenance.json",
                    "bm25_rag/answers.jsonl", "selected_pipeline/answers.jsonl")]
        required.append("runs/release-candidate/manifest.json")
        for optional in ([], [base + "fulltext/answers.jsonl"],
                         [base + "fulltext/answers.jsonl", base + "recovery-lineage.json"]):
            with self.subTest(optional=optional):
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    for name in required + optional:
                        archive.writestr(name, "sample")
                with zipfile.ZipFile(buffer) as archive:
                    self.assertEqual(previous_result_members(archive), sorted(required + optional))

    def test_new_input_backs_up_failed_working_run_before_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            old_archive = make_bundle(tmp / "old")
            new_archive = make_bundle(tmp / "new")
            input_root = tmp / "input"
            input_root.mkdir()
            shutil.copy2(new_archive, input_root / new_archive.name)
            working_root = tmp / "working/moroccan-constitution-rag"
            with zipfile.ZipFile(old_archive) as archive:
                archive.extractall(working_root)
            old_commit = restore_git_metadata(working_root)
            results = working_root / "runs/final-reserved-qwen4b-transformers"
            results.mkdir()
            (results / "manifest.json").write_text('{"run":"old"}\n')
            write_rows = results / "fulltext/answers.jsonl"
            write_rows.parent.mkdir()
            write_rows.write_text(json.dumps({"question_id": "q1", "answer": None,
                                             "error": {"type": "OutOfMemoryError"}}) + "\n")
            (working_root / "runs/release-candidate").mkdir()
            (working_root / "runs/release-candidate/manifest.json").write_text('{"commit":"old"}\n')
            notebook = json.loads(Path("notebooks/kaggle_final.ipynb").read_text())
            cell = "".join(notebook["cells"][1]["source"])
            cell = cell.replace("/kaggle/input", str(input_root))
            cell = cell.replace("/kaggle/working/moroccan-constitution-rag", str(working_root))
            exec(compile(cell, "kaggle_final_first_cell", "exec"), {})
            self.assertNotEqual(restore_git_metadata(working_root), old_commit)
            backups = list(working_root.parent.glob("constitution-final-results-before-upgrade-*.zip"))
            self.assertEqual(len(backups), 1)
            with zipfile.ZipFile(backups[0]) as archive:
                self.assertEqual(json.loads(archive.read(
                    "runs/final-reserved-qwen4b-transformers/fulltext/answers.jsonl"))
                    ["error"]["type"], "OutOfMemoryError")

    def test_upgrade_preserves_successful_fulltext_run(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            old_archive = make_bundle(tmp / "old")
            new_archive = make_bundle(tmp / "new")
            input_root = tmp / "input"
            input_root.mkdir()
            shutil.copy2(new_archive, input_root / new_archive.name)
            working_root = tmp / "working/moroccan-constitution-rag"
            with zipfile.ZipFile(old_archive) as archive:
                archive.extractall(working_root)
            previous = working_root / "runs/final-reserved-qwen4b-transformers/fulltext/answers.jsonl"
            previous.parent.mkdir(parents=True)
            previous.write_text(json.dumps({"question_id": "q1", "answer": {"status": "answered"},
                                            "error": None}) + "\n")
            notebook = json.loads(Path("notebooks/kaggle_final.ipynb").read_text())
            cell = "".join(notebook["cells"][1]["source"])
            cell = cell.replace("/kaggle/input", str(input_root))
            cell = cell.replace("/kaggle/working/moroccan-constitution-rag", str(working_root))
            with self.assertRaisesRegex(RuntimeError, "1 successful full-text answers"):
                exec(compile(cell, "kaggle_final_first_cell", "exec"), {})
            self.assertTrue(previous.exists())
            self.assertEqual(len(list(working_root.parent.glob(
                "constitution-final-results-before-upgrade-*.zip"))), 1)
