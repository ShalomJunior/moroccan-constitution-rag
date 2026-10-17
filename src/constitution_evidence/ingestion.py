"""Page-aware OCR and article extraction. OCR output requires human review."""
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from .corrections import apply_page_corrections
from .store import ROOT, corpus_paths, digest, write_jsonl

ARTICLE = re.compile(r"^\s*['‘]?\s*(?:Article|Artiele)\s+(premier|1er|\d{1,3})(?:\s*[|L])?\s*$", re.IGNORECASE)
HEADER = re.compile(r"^(?:N[°o]\s*\d|BULLETIN OFFICIEL|\d{4}\s+BULLETIN OFFICIEL|\d{4}\s*$)", re.IGNORECASE)

def clean_page(text: str) -> str:
    lines = []
    for line in text.replace("\r", "").splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if HEADER.match(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()

def parse_articles(pages: list[str], edition_id: str = "ma-constitution-2011") -> list[dict]:
    articles = []
    current = None
    preamble = []
    preamble_pages = set()
    preamble_heading_page = None
    def finish(article: dict) -> dict:
        lines = article.pop("lines")
        line_pages = article.pop("line_pages")
        while lines and not lines[0]:
            lines.pop(0)
            line_pages.pop(0)
        while lines and not lines[-1]:
            lines.pop()
            line_pages.pop()
        article["canonical_text"] = "\n".join(lines)
        segments = []
        offset = 0
        for line, page in zip(lines, line_pages):
            if line:
                segments.append({"start": offset, "end": offset + len(line), "page": page})
            offset += len(line) + 1
        article["page_segments"] = segments
        article["text_hash"] = digest(article["canonical_text"])
        return article
    for page_number, page in enumerate(pages, 1):
        for line in clean_page(page).splitlines():
            if preamble_heading_page is None and re.fullmatch(r"PR[EÉ]AMBULE", line, re.IGNORECASE):
                preamble_heading_page = page_number
            if current and current["article_number"] == 180 and line == "CONSEIL CONSTITUTIONNEL":
                break
            match = ARTICLE.match(line)
            if match:
                if current:
                    articles.append(finish(current))
                number = 1 if match.group(1).lower() in {"premier", "1er"} else int(match.group(1))
                current = {"article_id": f"{edition_id}:fr:art-{number}", "article_number": number,
                           "page_spans": [page_number], "lines": [], "line_pages": []}
            elif current:
                if line and page_number not in current["page_spans"]:
                    current["page_spans"].append(page_number)
                current["lines"].append(line)
                current["line_pages"].append(page_number)
            else:
                preamble.append(line)
                preamble_pages.add(page_number)
    if current:
        articles.append(finish(current))
    # Preamble location is edition-specific; only retain the portion after its heading.
    before = "\n".join(preamble)
    heading = re.search(r"(?im)^\s*PR[EÉ]AMBULE\s*$", before)
    if heading:
        value = before[heading.end():].strip()
        articles.insert(0, {"article_id": f"{edition_id}:fr:preamble", "article_number": 0,
                            "page_spans": sorted(page for page in preamble_pages if preamble_heading_page is None or page >= preamble_heading_page),
                            "canonical_text": value, "text_hash": digest(value)})
    return articles

def validate_articles(articles: list[dict], expected: int = 180) -> None:
    if not articles or articles[0]["article_number"] != 0 or not articles[0]["canonical_text"].strip():
        raise ValueError("Preamble missing or empty")
    numbers = [a["article_number"] for a in articles if a["article_number"] != 0]
    missing = sorted(set(range(1, expected + 1)) - set(numbers))
    duplicates = sorted(n for n in set(numbers) if numbers.count(n) > 1)
    extra = sorted(set(numbers) - set(range(1, expected + 1)))
    if missing or duplicates or extra or numbers != list(range(1, expected + 1)):
        raise ValueError(f"Article inventory invalid: missing={missing}, duplicate={duplicates}, extra={extra}, ordered={numbers == list(range(1, expected + 1))}")
    if any(len(a["canonical_text"]) < 30 for a in articles if a["article_number"] != 0):
        raise ValueError("An article is suspiciously short")

def validate_passages(articles: list[dict], passages: list[dict]) -> None:
    parents = {a["article_id"]: a for a in articles}
    seen = set()
    for passage in passages:
        pid = passage["passage_id"]
        if pid in seen:
            raise ValueError(f"Duplicate passage ID: {pid}")
        seen.add(pid)
        article = parents.get(passage["article_id"])
        if article is None:
            raise ValueError(f"Unknown parent article: {pid}")
        start, end = passage["char_start"], passage["char_end"]
        if not 0 <= start < end <= len(article["canonical_text"]):
            raise ValueError(f"Invalid offsets: {pid}")
        value = article["canonical_text"][start:end]
        if value != passage["canonical_text"] or digest(value) != passage["text_hash"]:
            raise ValueError(f"Passage text/hash mismatch: {pid}")
        if not set(passage["page_spans"]) <= set(article["page_spans"]):
            raise ValueError(f"Passage page mismatch: {pid}")

def make_passages(articles: list[dict]) -> list[dict]:
    result = []
    for article in articles:
        body = article["canonical_text"]
        # Preserve exact offsets in the canonical article text.
        spans = [m.span() for m in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", body)]
        if not spans:
            spans = [(0, len(body))]
        for idx, (start, end) in enumerate(spans, 1):
            value = body[start:end]
            if not value.strip():
                continue
            result.append({"passage_id": f"{article['article_id']}:p-{idx}", "article_id": article["article_id"],
                           "article_number": article["article_number"], "paragraph_index": idx,
                           "char_start": start, "char_end": end, "canonical_text": value,
                           "text_hash": digest(value),
                           "page_spans": sorted({segment["page"] for segment in article.get("page_segments", [])
                                                 if segment["end"] > start and segment["start"] < end}) or article["page_spans"],
                           "token_count": len(value.split())})
    return result

def extract_pages(pdf: Path, pages_dir: Path, dpi: int = 170, tessdata: Path | None = None) -> list[str]:
    pages_dir.mkdir(parents=True, exist_ok=True)
    info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
    count = int(re.search(r"(?m)^Pages:\s+(\d+)", info).group(1))
    output = []
    for page in range(1, count + 1):
        target = pages_dir / f"page-{page:03d}.txt"
        if not target.exists():
            native = subprocess.check_output(["pdftotext", "-f", str(page), "-l", str(page), str(pdf), "-"], text=True)
            if len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", native)) > 100 and "Article" in native:
                target.write_text(native, encoding="utf-8")
            else:
                if not tessdata or not (tessdata / "fra.traineddata").exists():
                    raise RuntimeError("French OCR data missing. Put fra.traineddata in data/ocr or set --tessdata.")
                import os
                env = dict(os.environ, TESSDATA_PREFIX=str(tessdata))
                with tempfile.TemporaryDirectory() as temp:
                    image = Path(temp) / "page"
                    subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(dpi), "-png", "-singlefile", str(pdf), str(image)], check=True, capture_output=True)
                    recognized = subprocess.run(["tesseract", str(image) + ".png", "stdout", "-l", "fra"], capture_output=True, check=True, env=env)
                target.write_bytes(recognized.stdout)
        output.append(target.read_text(encoding="utf-8"))
    return output

def ingest(config_path: Path, root: Path = ROOT, tessdata: Path | None = None,
           corrections: Path | None = None) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pdf = root / config["pdf_path"]
    pdf_bytes = pdf.read_bytes()
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Source is not a PDF")
    ocr_dir = tessdata or root / "data/ocr"
    pdf_hash = digest(pdf_bytes)
    language_file = ocr_dir / "fra.traineddata"
    language_hash = digest(language_file.read_bytes()) if language_file.exists() else None
    dpi = config.get("ocr_dpi", 170)
    cache_key = digest(f"{pdf_hash}:{dpi}:{language_hash}")[:16]
    pages = extract_pages(pdf, root / "data/processed/pages" / cache_key, dpi, ocr_dir)
    correction_path = corrections or root / "data/annotations/ocr-corrections.jsonl"
    pages, corrections_hash, correction_count = apply_page_corrections(pages, correction_path, pdf_hash)
    articles = parse_articles(pages, config["edition_id"])
    validate_articles(articles, config["expected_articles"])
    passages = make_passages(articles)
    validate_passages(articles, passages)
    article_path, passage_path, manifest_path = corpus_paths(root)
    write_jsonl(article_path, articles)
    write_jsonl(passage_path, passages)
    manifest = {"source_id": config["edition_id"] + ":fr", "edition_id": config["edition_id"], "language": "fr", "text_version": "2011",
                "source_url": config["source_url"], "source_page": config["source_page"],
                "pdf_sha256": pdf_hash, "page_count": len(pages),
                "article_count": len(articles) - int(articles[0]["article_number"] == 0),
                "passage_count": len(passages), "corpus_hash": digest(article_path.read_bytes()),
                "passages_hash": digest(passage_path.read_bytes()),
                "extraction_method": "native text or French Tesseract OCR per page", "parser_version": "fr-ocr-v1",
                "ocr_dpi": dpi, "page_cache_key": cache_key,
                "tesseract_version": subprocess.check_output(["tesseract", "--version"], text=True, stderr=subprocess.STDOUT).splitlines()[0],
                "fra_traineddata_sha256": language_hash,
                "ocr_corrections_sha256": corrections_hash, "ocr_correction_count": correction_count,
                "ingested_at": datetime.now(timezone.utc).isoformat(), "review_status": "unreviewed_ocr"}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
