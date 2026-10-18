"""Explicit human signoff for a complete French corpus review."""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from .store import digest, read_jsonl, write_jsonl


def _inputs(articles_path: Path, manifest_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if digest(articles_path.read_bytes()) != manifest["corpus_hash"]:
        raise ValueError("Articles differ from the corpus manifest")
    articles = read_jsonl(articles_path)
    if len(articles) != manifest["article_count"] + 1 or {a["article_number"] for a in articles} != set(range(181)):
        raise ValueError("French article inventory is incomplete")
    return articles, manifest


def create_review_template(articles_path: Path, manifest_path: Path, output_path: Path) -> dict:
    articles, manifest = _inputs(articles_path, manifest_path)
    if output_path.exists():
        raise ValueError("Review file already exists; preserve completed review records")
    rows = [{"article_number": article["article_number"], "article_text_hash": article["text_hash"],
             "pdf_sha256": manifest["pdf_sha256"], "page_spans": article["page_spans"],
             "pdf_checked": False, "reviewer": "", "reviewed_at": "", "notes": ""}
            for article in articles]
    write_jsonl(output_path, rows)
    return {"path": str(output_path), "units": len(rows), "pdf_sha256": manifest["pdf_sha256"]}


def certify_corpus(articles_path: Path, manifest_path: Path, review_path: Path) -> dict:
    articles, manifest = _inputs(articles_path, manifest_path)
    rows = read_jsonl(review_path)
    if len(rows) != len(articles) or len({r.get("article_number") for r in rows}) != len(articles):
        raise ValueError("Review must contain exactly one record per French unit")
    by_number = {r["article_number"]: r for r in rows}
    for article in articles:
        number = article["article_number"]
        row = by_number.get(number)
        if not row or row.get("pdf_sha256") != manifest["pdf_sha256"] or row.get("article_text_hash") != article["text_hash"] or row.get("page_spans") != article["page_spans"]:
            raise ValueError(f"Review source or text changed for unit {number}")
        if row.get("pdf_checked") is not True or not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
            raise ValueError(f"PDF comparison has not been signed for unit {number}")
        try:
            stamp = datetime.fromisoformat(row["reviewed_at"])
            if stamp.tzinfo is None:
                raise ValueError("timezone is required")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Review timestamp is invalid for unit {number}") from exc
    updated = {**manifest, "review_status": "reviewed", "review_file_sha256": digest(review_path.read_bytes()),
               "reviewed_units": len(rows), "reviewers": sorted({r["reviewer"].strip() for r in rows})}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=manifest_path.parent, delete=False) as stream:
        json.dump(updated, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = stream.name
    os.replace(temporary, manifest_path)
    return {"status": "reviewed", "units": len(rows), "corpus_hash": manifest["corpus_hash"],
            "review_file_sha256": updated["review_file_sha256"]}
