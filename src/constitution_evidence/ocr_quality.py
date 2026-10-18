"""Reproducible OCR triage over the active canonical French corpus."""
import re
from collections import Counter
from pathlib import Path

from .ingestion import validate_articles, validate_passages
from .store import digest, read_jsonl

FUSED_LINE_START = re.compile(r"^F[a-zà-ÿ]{4,}\b")
MIXED_TOKEN = re.compile(r"\b(?=[A-Za-zÀ-ÿ0-9]*[A-Za-zÀ-ÿ])(?=[A-Za-zÀ-ÿ0-9]*\d)[A-Za-zÀ-ÿ0-9]{3,}\b")
ORDINAL = re.compile(r"\d+(?:er|e|ème)", re.IGNORECASE)
STRAY_MARK = re.compile(r"[A-Za-zÀ-ÿ][|^~][A-Za-zÀ-ÿ]")


def find_risks(articles: list[dict]) -> list[dict]:
    """Return candidates, not confirmed errors or an OCR accuracy estimate."""
    findings = []
    for article in articles:
        previous = ""
        for line_number, line in enumerate(article["canonical_text"].splitlines(), 1):
            stripped = line.strip()
            kinds = []
            if "\ufffd" in line or any(ord(char) < 32 and char not in "\t" for char in line):
                kinds.append("replacement_or_control_character")
            if any(not ORDINAL.fullmatch(match.group()) for match in MIXED_TOKEN.finditer(line)):
                kinds.append("letters_and_digits_in_one_token")
            if STRAY_MARK.search(line):
                kinds.append("stray_mark_inside_word")
            if FUSED_LINE_START.match(stripped) and re.search(r"\b(?:à|de|du|des|pour|par)$", previous, re.I):
                kinds.append("possible_fused_apostrophe_after_preposition")
            for kind in kinds:
                findings.append({"article_number": article["article_number"],
                                 "page_spans": article["page_spans"],
                                 "line_number": line_number, "kind": kind,
                                 "text": stripped[:180]})
            if stripped:
                previous = stripped
    return findings


def write_risk_audit(articles_path: Path, passages_path: Path, manifest_path: Path,
                     output: Path) -> dict:
    import json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if digest(articles_path.read_bytes()) != manifest["corpus_hash"] or digest(passages_path.read_bytes()) != manifest["passages_hash"]:
        raise ValueError("Active corpus differs from manifest")
    articles, passages = read_jsonl(articles_path), read_jsonl(passages_path)
    validate_articles(articles)
    validate_passages(articles, passages)
    findings = find_risks(articles)
    counts = Counter(row["kind"] for row in findings)
    lines = ["# Automated French OCR risk audit", "",
             f"Corpus SHA-256: `{manifest['corpus_hash']}`  ",
             f"Passages SHA-256: `{manifest['passages_hash']}`  ",
             f"Review status: `{manifest['review_status']}`  ",
             f"Recorded page corrections: {manifest.get('ocr_correction_count', 0)}", "",
             f"Validated inventory: {len(articles)-1} numbered articles, one preamble, {len(passages)} passages.",
             "This scan finds patterns that may indicate OCR damage. It does not compare text with PDF images and cannot estimate error rate or establish legal accuracy.",
             "", "## Candidate findings", ""]
    if findings:
        lines.extend(["| Article | PDF page | Line | Pattern | Canonical text |",
                      "| ---: | ---: | ---: | --- | --- |"])
        for row in findings:
            safe = row["text"].replace("|", "\\|").replace("`", "\\`")
            pages = ", ".join(map(str, row["page_spans"]))
            lines.append(f"| {row['article_number']} | {pages} | {row['line_number']} | {row['kind']} | {safe} |")
    else:
        lines.append("No patterns matched. This does not mean the OCR is error-free.")
    interpretation = ("Findings are triage candidates. A reviewer must compare a candidate with its PDF page before changing the correction journal. "
                      "Plausible but wrong words, missing negations, and omitted lines may escape these rules. "
                      "The scan does not replace the separately recorded human PDF review.")
    lines.extend(["", "## Interpretation", "", interpretation, ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return {"path": str(output), "corpus_hash": manifest["corpus_hash"],
            "finding_count": len(findings), "by_kind": dict(counts),
            "review_status": manifest["review_status"]}
