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

The command checks question and passage hashes, row completeness, passage IDs, and every article/evidence metric against saved hits. It rejects changed labels or tampered metrics before aggregating. It makes no provider request. For the final human scores, use `score-review-verdicts --packets <private-packets.jsonl> --mapping <private-mapping.jsonl> --reviews <authoritative-review.jsonl>`. The command verifies the 205 reviewed rows against the blind packet and counts all 65 technical errors as failures. `score-judgments` applies only to the superseded four-criterion review. Keep all three final input files private.

## Demo and release

The reviewed validation comparison on the current corpus used 45 French questions, 10 retrieved articles, and a 7,000-character context budget. With the private reviewed benchmark supplied as `--questions`, rerun `evaluate --split validation` for `bm25`, `dense`, and `hybrid`, then pass those run IDs to `select-validation`. The command saves `runs/validation-selection.json`; keep that file and the run directories with the private benchmark. Hybrid covered a complete acceptable evidence set for 37/39 answerable validation questions, BM25 for 34/39, and dense for 32/39. The `hybrid-rerank` evaluation was started but not completed on the available CPU, so it was excluded from the selection. `configs/final_systems.json` fixes the selected hybrid method and the common Qwen3-4B prompt for the three-system comparison. These are retrieval results, not measured answer quality.

`constitution-evidence serve` binds to loopback. A default extractive question requires no API key. Groq generation needs a key kept outside Git; local Qwen needs a separately installed server and model as described in `docs/local-model.md`. The 4,096-token CPU setup cannot fit the full-text baseline. The frozen Qwen3-4B Kaggle run and the second-reviewer blind verdicts are summarized in [the final evaluation](../reports/final-evaluation.md). They do not evaluate the application's Groq mode.

Run `constitution-evidence publication-audit` before publishing; it inspects tracked file paths, file sizes, and common credential patterns. It is a screening check, not a legal opinion or complete secret scanner. The repository must not include downloaded PDF files, OCR/model weights, generated corpus, private `.env`, or run outputs without an explicit rights and privacy review. The frozen release manifest was ready at commit `726abe0632f027dd430e4bac405ca0b66513b8c6` before the reserved test. The `1.0.2` packaging and report changes are subsequent to that frozen execution and do not retroactively change its results. To rerun `test-preflight` against that manifest, check out the frozen commit and supply its private bundle; the command intentionally rejects a later source revision.

The corpus, annotations, final systems, test answers, and final categorical review are complete. Their hashes and computed statistics are in [the final evaluation](../reports/final-evaluation.md); the private question and response artifacts remain under ignored `runs/`. CI performs a fresh-checkout install from `uv.lock`; the PDF link and local PDF hash were checked for this release. Keep the v1 reserved test separate from any later extension test.

For the frozen three-system GPU run, follow [the Kaggle final evaluation guide](kaggle-final.md). Its private bundle is built from the clean release commit and includes the already reviewed corpus and benchmark. The earlier Kaggle calibration notebooks are separate experiments.
