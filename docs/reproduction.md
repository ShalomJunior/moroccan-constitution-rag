# Reproduction and publication checklist

## Clean environment

From a fresh clone with Python 3.12 and [uv](https://docs.astral.sh/uv/) installed, use `uv sync --frozen --extra api --extra dense --extra groq --no-dev`. This installs dependencies from `uv.lock`; the program does not install packages at runtime. Run `.venv/bin/python -m unittest discover -s tests -v` and `.venv/bin/constitution-evidence --help`. CI runs an offline test suite, and the Docker image has been built with the locked API, dense, and Groq extras. A fresh-clone dependency install on another machine remains a separate release check.

Acquire the French source PDF at the URL in `configs/corpus.json` and verify SHA-256 `4101d45b4733a6b36eee77bd9ef4175b23160103089b003b13907e8b6d59333d`. Acquire French Tesseract language data with SHA-256 `ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca`. Keep these in the ignored `data/raw` and `data/ocr` directories. Run `constitution-evidence ingest`, `validate-corpus`, and `audit-corpus`. Re-ingestion starts with `unreviewed_ocr`; replay `certify-corpus` against the tracked single-reviewer journal only if its 181 article hashes still match. Compare output hashes against the active manifest; if versions differ, label the new run rather than reusing published metrics.

## Recalculate tables without a model or API

The historical robustness questions are in `data/annotations/robustness_calibration.jsonl`; their published results use the earlier OCR corpus. The current 15-question search checks use `data/annotations/calibration.jsonl` and fresh `external-review-final-*` run IDs. Regenerate runs with `constitution-evidence evaluate --questions data/annotations/calibration.jsonl --run-id external-review-final-bm25 --strategy bm25`, and analogously for `dense` and `hybrid`. The generated `runs/` directory is ignored by Git. If saved run artifacts are transferred separately, verify and recompute them with:

```bash
constitution-evidence reproduce-retrieval --questions data/annotations/calibration.jsonl \
  external-review-final-bm25 external-review-final-hybrid
```

The command checks question and passage hashes, row completeness, passage IDs, and every article/evidence metric against saved hits. It rejects changed labels or tampered metrics before aggregating. It makes no provider request. For final human scores, use `score-judgments` with finalized blind judgments and the private mapping. Never publish the private mapping alongside still-blind packets.

## Demo and release

`constitution-evidence serve` binds to loopback. A default extractive question requires no API key. Groq generation needs a key kept outside Git; local Qwen needs a separately installed server and model as described in `docs/local-model.md`. The 4,096-token CPU setup cannot fit the full-text baseline. The Kaggle Transformers notebook completed a historical Qwen 4B experiment on an earlier corpus; it is not a final baseline on the current reviewed corpus.

Run `constitution-evidence publication-audit` before publishing; it inspects tracked file paths, file sizes, and common credential patterns. It is a screening check, not a legal opinion or complete secret scanner. The repository must not include downloaded PDF files, OCR/model weights, generated corpus, private `.env`, or run outputs without an explicit rights and privacy review. Run `release-readiness` and `test-preflight`. The `0.1.0` application release does not satisfy the gate for a final evaluated `v1.0` release.

Once corpus, annotations, final systems, and blind judgments are complete, archive their hashes, reproduce all tables, run a fresh-clone install, verify the PDF/source links, and only then prepare a release candidate and tag through the Gitflow procedure. Keep v1 test data separate from any J41–J50 extension test.
