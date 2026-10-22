"""Resolve a reviewer-selected literal quote to canonical passage offsets."""
from pathlib import Path

from .store import digest, read_jsonl


def locate_span(passages_path: Path, manifest: dict, passage_id: str, quote: str) -> dict:
    if manifest.get("review_status") != "reviewed" or digest(passages_path.read_bytes()) != manifest.get("passages_hash"):
        raise ValueError("Evidence spans require the active reviewed corpus")
    if not passage_id or not quote.strip():
        raise ValueError("Passage ID and nonempty quote are required")
    matches = [row for row in read_jsonl(passages_path) if row["passage_id"] == passage_id]
    if len(matches) != 1:
        raise ValueError("Passage ID is missing or duplicated")
    text = matches[0]["canonical_text"]
    start = text.find(quote)
    if start < 0:
        raise ValueError("Quote is not an exact substring of the passage")
    if text.find(quote, start + 1) >= 0:
        raise ValueError("Quote occurs more than once; select a longer unique quote")
    return {"passage_id": passage_id, "char_start": start, "char_end": start + len(quote),
            "quote": quote, "source_hash": matches[0]["text_hash"],
            "article_number": matches[0]["article_number"]}
