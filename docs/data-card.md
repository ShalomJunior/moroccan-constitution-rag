# Data card: French 2011 Moroccan Constitution development corpus

## Origin and intended use

The source is the 28-page [Maroc.ma institutional PDF](https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf) for the 2011 Constitution of Morocco. The project uses its French text for passage retrieval and inspectable documentary answers. It is not a current-law database, legal advice system, or authoritative corrected edition. Arabic text and Arabic evaluation are outside this project scope by user request.

The downloaded PDF has SHA-256 `4101d45b4733a6b36eee77bd9ef4175b23160103089b003b13907e8b6d59333d`. `configs/corpus.json` records the URL, edition ID, language, and expected article count. The PDF and derived OCR are local inputs excluded from Git. This project has not established redistribution permission for the PDF or a derivative corrected transcription. Reproducers should acquire the source independently and inspect the applicable terms before republishing.

## Processing and current inventory

Poppler and French Tesseract OCR produce page text, followed by a parser for the preamble and articles. Derived article and paragraph records preserve canonical text, article numbers, page spans, offsets, and hashes. The present development build has 180 articles plus a preamble, and 633 passages. Its article hash is `8a80b613971b6b7ffde76cefea14e582a289738546356a15c446ee10854eeb90`; passage hash is `2b7c534cbc06db05526bf95c17fbeb27460d329191e45f4a5a34f54eab590dd1`. The actual local `data/processed/manifest.json` is the machine-readable authority for the current build and says `unreviewed_ocr`.

No full article-by-article PDF comparison has occurred. OCR can alter negations, dates, article boundaries, or words used in search. Inventory, page, and hash checks establish internal consistency only. A correction workflow records exact source-page edits, but no correction should be treated as reviewed without checking the PDF. Any corrected corpus will have new hashes, and old passage offsets and labels may need migration.

## Annotations and splits

The tracked `data/annotations/calibration.jsonl` has 15 author-written provisional French development questions with article labels. `robustness_calibration.jsonl` has 45 direct, paraphrased, and typo variants in the same 15 families. `dialogue_calibration.jsonl` contains parser-oriented short-dialogue fixtures. These are smoke checks, not the planned 45/45/90 reviewed benchmark and not independent legal judgments. No answer-level human labels or reviewed gold spans have been released.

Future benchmark records must include family IDs, split, expected status, reviewed evidence where applicable, corpus hash, annotator and review status. Paraphrases remain in one family split. A second reviewer should inspect at least the planned sample when available. The reserved test cannot guide model selection.

## Access, limitations, and maintenance

The Git repository contains code, configuration, provisional questions, and documentation. It excludes raw PDFs, OCR language files, generated corpus, model weights, and run outputs. The French source is linked from each answer to a PDF page. Users must inspect the original page before relying on a provision. A verbatim excerpt may be relevant but incomplete; an exact model quote may fail to support the attached claim. The release gate blocks final evaluation while OCR, labels, and model choices are unfinished.

Rebuild with the pinned source URL and SHA-256, the recorded French OCR language file hash, and `uv.lock`; run `validate-corpus` and inspect the audit report. If the institution updates or replaces the PDF, preserve the old hash, create a new corpus version, and rerun annotation and evaluation rather than silently overwriting results.
