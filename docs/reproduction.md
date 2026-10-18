# Reproduction and publication checklist

## Clean environment

From a fresh clone with Python 3.12 and [uv](https://docs.astral.sh/uv/) installed, use `uv sync --frozen --extra api --no-dev`. Add `--extra dense` for the recorded dense and hybrid retrieval runs. This installs dependencies from `uv.lock`; the program does not install packages at runtime. Run `.venv/bin/python -m unittest discover -s tests -v` and `.venv/bin/constitution-evidence --help`. The CI workflow runs this install and offline suite. A committed `git archive` copy passed all 41 tests using the existing pinned environment on 2026-10-18. A fresh-clone **dependency install** has not yet been executed outside the current machine; report this as a remaining release check.

Acquire the French source PDF at the URL in `configs/corpus.json` and verify SHA-256 `4101d45b4733a6b36eee77bd9ef4175b23160103089b003b13907e8b6d59333d`. Acquire French Tesseract language data with SHA-256 `ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca`. Keep these in the ignored `data/raw` and `data/ocr` directories. Run `constitution-evidence ingest`, `validate-corpus`, and `audit-corpus`. Compare output hashes against the run manifest; if versions differ, label the new run rather than reusing published metrics.

## Recalculate tables without a model or API

The tracked provisional question file is `data/annotations/robustness_calibration.jsonl`. Regenerate runs with `constitution-evidence evaluate --questions data/annotations/robustness_calibration.jsonl --run-id french-robustness-bm25 --strategy bm25`, and analogously for `dense` and `hybrid`. The generated `runs/` directory is ignored by Git. If saved run artifacts are transferred separately, verify and recompute them with:

```bash
constitution-evidence reproduce-retrieval \
  french-robustness-bm25 french-robustness-hybrid
```

The command checks question and passage hashes, row completeness, passage IDs, and every article/evidence metric against saved hits. It rejects changed labels or tampered metrics before aggregating. It makes no provider request. For final human scores, use `score-judgments` with finalized blind judgments and the private mapping. Never publish the private mapping alongside still-blind packets.

## Demo and release

`constitution-evidence serve` binds to loopback. A default extractive question requires no API key; the optional local Qwen demonstration needs a separately installed llama.cpp server and model as described in `docs/local-model.md`. The local model is not a full-text baseline under its present context budget. No external API key was available for a full-text baseline at the time of this report.

Run `constitution-evidence publication-audit` before publishing; it inspects tracked file paths, file sizes, and common credential patterns. It is a screening check, not a legal opinion or complete secret scanner. The repository must not include downloaded PDF files, OCR/model weights, generated corpus, private `.env`, or run outputs without an explicit rights and privacy review. Run `release-readiness` and `test-preflight`. Do not tag `v1.0` while either reports a block. The current state is a development build, not a finished evaluated release.

Once corpus, annotations, final systems, and blind judgments are complete, archive their hashes, reproduce all tables, run a fresh-clone install, verify the PDF/source links, and only then prepare a release candidate and tag through the Gitflow procedure. Keep v1 test data separate from any J41–J50 extension test.
