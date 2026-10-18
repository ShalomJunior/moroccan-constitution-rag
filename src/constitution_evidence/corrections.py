"""Explicit, source-anchored OCR corrections and a reviewable corpus report."""
import html
import os
from pathlib import Path
from urllib.parse import quote
from .store import digest, read_jsonl

def apply_page_corrections(pages: list[str], corrections_path: Path, pdf_hash: str) -> tuple[list[str], str | None, int]:
    """Apply exact replacements to OCR pages before parsing articles.

    A correction is never inferred from a model. Its raw-page hash and the PDF
    hash must match, so a changed extraction cannot silently reuse it.
    """
    if not corrections_path.exists():
        return pages, None, 0
    raw = corrections_path.read_bytes()
    corrections = read_jsonl(corrections_path)
    original_hashes = [digest(page) for page in pages]
    corrected = pages.copy()
    seen_ids = set()
    for row in corrections:
        required = ("correction_id", "page", "source_pdf_sha256", "ocr_page_sha256",
                    "old", "new", "reason", "reviewer")
        if any(key not in row for key in required):
            raise ValueError(f"OCR correction requires {', '.join(required)}")
        cid = row["correction_id"]
        if not isinstance(cid, str) or not cid.strip() or cid in seen_ids:
            raise ValueError(f"Duplicate or empty OCR correction ID: {cid}")
        seen_ids.add(cid)
        page = row["page"]
        if not isinstance(page, int) or isinstance(page, bool) or not 1 <= page <= len(pages):
            raise ValueError(f"Invalid page in correction {cid}")
        if row["source_pdf_sha256"] != pdf_hash or row["ocr_page_sha256"] != original_hashes[page - 1]:
            raise ValueError(f"Source PDF or OCR page changed for correction {cid}")
        if any(not isinstance(row[key], str) or not row[key].strip() for key in ("old", "reason", "reviewer")):
            raise ValueError(f"Correction {cid} needs exact old text, reason, and reviewer")
        if not isinstance(row["new"], str):
            raise ValueError(f"Correction {cid} has invalid replacement text")
        count = corrected[page - 1].count(row["old"])
        if count != 1:
            raise ValueError(f"Correction {cid} matched {count} times on OCR page {page}; expected exactly one")
        corrected[page - 1] = corrected[page - 1].replace(row["old"], row["new"], 1)
    return corrected, digest(raw), len(corrections)

def write_audit_html(articles: list[dict], manifest: dict, output: Path,
                     pdf_path: Path | None = None, pages_dir: Path | None = None) -> dict:
    """Make a static page-by-page review aid; it never changes review status."""
    output.parent.mkdir(parents=True, exist_ok=True)
    source = manifest["source_url"]
    local_pdf = quote(os.path.relpath(pdf_path, output.parent)) if pdf_path else None
    sections = []
    for article in articles:
        number = article["article_number"]
        title = "Préambule" if number == 0 else f"Article {number}"
        links = " ".join(
            f'<a href="{html.escape(local_pdf or source, quote=True)}#page={page}" target="_blank" rel="noopener noreferrer">PDF p. {page}</a>'
            for page in article["page_spans"])
        text = article["canonical_text"]
        sections.append(
            f'<section id="unit-{number}"><h2>{title}</h2><p>{links} · {len(text)} caractères'
            f' · SHA-256 <code>{html.escape(article["text_hash"])}</code></p>'
            f'<pre>{html.escape(text)}</pre></section>')
    navigation = " ".join(f'<a href="#unit-{a["article_number"]}">{"P" if a["article_number"] == 0 else a["article_number"]}</a>'
                          for a in articles)
    raw_pages = ""
    if pages_dir:
        entries = []
        for page_file in sorted(pages_dir.glob("page-*.txt")):
            page_number = int(page_file.stem.split("-")[-1])
            href = quote(os.path.relpath(page_file, output.parent))
            entries.append(f'<li>Page {page_number}: <a href="{html.escape(href, quote=True)}">OCR brut</a>'
                           f' · SHA-256 <code>{digest(page_file.read_bytes())}</code></li>')
        raw_pages = "<details><summary>Pages OCR brutes et hashes pour les corrections</summary><ul>" + "".join(entries) + "</ul></details>"
    page = ("<!doctype html><html lang=\"fr\"><meta charset=\"utf-8\"><title>Revue OCR française</title>"
            "<style>body{font:16px system-ui;max-width:1050px;margin:auto;padding:2rem;color:#18212b}"
            "nav{line-height:2.2}nav a{margin-right:.5rem}section{border-top:1px solid #bbb;padding:1rem 0}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.55 ui-monospace,monospace}"
            "a{color:#0757a6}</style>"
            f"<h1>Revue OCR française</h1><p>Statut : <strong>{html.escape(manifest['review_status'])}</strong>. "
            "Ce rapport aide à comparer le texte extrait aux pages du PDF ; il ne valide aucun article.</p>"
            f"<p>PDF SHA-256 : <code>{html.escape(manifest['pdf_sha256'])}</code> · "
            f"Corpus SHA-256 : <code>{html.escape(manifest['corpus_hash'])}</code></p>"
            f"{raw_pages}<nav>{navigation}</nav>{''.join(sections)}</html>")
    output.write_text(page, encoding="utf-8")
    return {"path": str(output), "units": len(articles), "review_status": manifest["review_status"],
            "corpus_hash": manifest["corpus_hash"]}
