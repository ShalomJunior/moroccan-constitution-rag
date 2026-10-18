# Data card: French 2011 Moroccan Constitution development corpus

## Origin and intended use

The source is the 28-page [Maroc.ma institutional PDF](https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf) for the 2011 Constitution of Morocco. The project uses its French text for passage retrieval and inspectable documentary answers. It is not a current-law database, legal advice system, or authoritative corrected edition. Arabic text and Arabic evaluation are outside the retained scope.

The downloaded PDF has SHA-256 `4101d45b4733a6b36eee77bd9ef4175b23160103089b003b13907e8b6d59333d`. `configs/corpus.json` records the URL, edition ID, language, and expected article count. The PDF and derived OCR are local inputs excluded from Git. This project has not established redistribution permission for the PDF or a derivative corrected transcription. Reproducers should acquire the source independently and inspect the applicable terms before republishing.

## Processing and current inventory

Poppler and French Tesseract OCR produce page text, followed by a parser for the preamble and articles. Derived article and passage records preserve canonical text, article numbers, page spans, offsets, and hashes. The current build has 180 articles plus a preamble and 483 passages. Its article hash is `c319ecb4cabe0eaafc3de18779cc210ec8fa83cffbaeb2259393073e9fb4901c`; its passage hash is `a4abf1b043a72c18d6dcc740f3f3ebbbc1a29aeebf0eedb8c1264d0793c5079c`. The local `data/processed/manifest.json` is the machine-readable authority for the active build and says `reviewed` after certification.

The project owner compared all 181 French units with the PDF. The correction journal contains 309 PDF- and raw-page-hash-anchored edits, including the earlier Article 27 correction. `data/annotations/corpus-review.jsonl` records the owner's self-attested, single-reviewer comparison, tied to each corrected article hash. The audit is not an independent legal review. OCR can still contain an overlooked error; inventory and hash checks establish internal consistency, not perfect transcription. Passage segmentation joins OCR blank lines that interrupt a sentence; this changed all passage IDs and offsets relative to earlier runs.

## Annotations and splits

The tracked `data/annotations/calibration.jsonl` has 15 provisional French development questions with article labels. `robustness_calibration.jsonl` has 45 direct, paraphrased, and typo variants in the same 15 families. `dialogue_calibration.jsonl` contains parser-oriented short-dialogue fixtures. The owner reviewed two sets of 15 generated answers; the [summary](../reports/development-answer-review.md) reports 7/15 and 8/15 strict successes. These are development checks, not the planned 45/45/90 benchmark. Reviewed gold evidence spans are still missing.

Future benchmark records must include family IDs, split, expected status, reviewed evidence where applicable, corpus hash, annotator and review status. Paraphrases remain in one family split. A second reviewer should inspect at least the planned sample when available. The reserved test cannot guide model selection.

## Access, limitations, and maintenance

The Git repository contains code, configuration, provisional questions, the correction journal, the corpus review record, and documentation. It excludes raw PDFs, OCR language files, generated corpus, model weights, raw review notes, and run outputs. The French source is linked from each answer to a PDF page. Users must inspect the original page before relying on a provision. A verbatim excerpt may be relevant but incomplete; an exact model quote may fail to support the attached claim. The release gate still blocks final evaluation while reviewed benchmark labels, validation selection, and fixed final systems are missing.

Rebuild with the pinned source URL and SHA-256, the recorded French OCR language file hash, and `uv.lock`; run `validate-corpus` and inspect the audit report. If the institution updates or replaces the PDF, preserve the old hash, create a new corpus version, and rerun annotation and evaluation rather than silently overwriting results.
