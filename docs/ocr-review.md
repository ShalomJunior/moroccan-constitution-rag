# French OCR review and correction

Run `constitution-evidence ingest`, then `constitution-evidence audit-corpus`. Open the generated `reports/ocr-audit.html` locally. It lists the preamble and every numbered article with its canonical text, page links, source hashes, and links to the raw OCR page files. Compare the complete text and each article boundary against the PDF image, including negations, numbers, names, and the end of article 180. The audit page is a review aid; generating it does not mark the corpus reviewed.

For a verified correction, add one JSON object per line to `data/annotations/ocr-corrections.jsonl`. Use the **raw OCR page** text for `old`, preserving its spaces and line breaks. Copy `source_pdf_sha256` and the raw page's `ocr_page_sha256` from the audit page. The replacement must match exactly once on that page. A correction can include a heading and surrounding lines when their OCR reading order needs repair.

```json
{"correction_id":"page-007-c01","page":7,"source_pdf_sha256":"<PDF hash from audit>","ocr_page_sha256":"<raw OCR page hash from audit>","old":"<exact OCR text>","new":"<text checked against PDF image>","reason":"Compared with PDF page 7","reviewer":"<name or author>"}
```

Then run `constitution-evidence ingest` and `constitution-evidence validate-corpus` again. Ingestion applies the corrections before parsing articles, rebuilds passages and offsets, and records the correction file's hash and count in `data/processed/manifest.json`. It rejects a correction when the PDF, raw OCR page, or target text has changed. Keep the correction journal under version control. Existing span annotations and retrieval runs tied to an older corpus hash need review or regeneration.

The manifest stays `unreviewed_ocr` until the whole French corpus and boundaries have been reviewed. A correction by the project author is documented work, not independent legal review. Do not set `review_status` by hand.
