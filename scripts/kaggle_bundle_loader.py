"""Restore Git provenance from a Kaggle bundle after dataset extraction."""

import base64
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path


def restore_git_metadata(root: Path) -> str:
    marker = json.loads((root / "runs/kaggle-bundle.json").read_text())
    commit = marker["commit"]
    if not (root / ".git").exists():
        encoded = marker.get("git_metadata_b64")
        digest = marker.get("git_metadata_sha256")
        if not encoded or not digest:
            raise RuntimeError(
                "This Kaggle input was made with an older bundle builder. "
                "Upload a newly built constitution-evidence-final-input.zip."
            )
        metadata = base64.b64decode(encoded, validate=True)
        if hashlib.sha256(metadata).hexdigest() != digest:
            raise RuntimeError("Git metadata in the Kaggle input failed its checksum")
        with tarfile.open(fileobj=io.BytesIO(metadata), mode="r:gz") as archive:
            archive.extractall(root, filter="data")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if actual != commit:
        raise RuntimeError(f"Kaggle input commit mismatch: expected {commit}, found {actual}")
    return actual
