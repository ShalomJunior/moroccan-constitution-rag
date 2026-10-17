import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing corpus: {path}. Run `constitution-evidence ingest`.")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        for item in records:
            stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        temporary = stream.name
    os.replace(temporary, path)

def corpus_paths(root: Path = ROOT) -> tuple[Path, Path, Path]:
    base = root / "data/processed"
    return base / "articles.jsonl", base / "passages.jsonl", base / "manifest.json"
