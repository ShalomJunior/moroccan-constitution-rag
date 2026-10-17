# Constitution Evidence

A French documentary QA project for Morocco's 2011 Constitution. It is under construction; the current answer path returns source excerpts, not verified legal conclusions. The detailed [roadmap](constitution-rag/roadmap.md), [implementation specification](constitution-rag/implementation-spec.md), and [evaluation protocol](constitution-rag/evaluation-protocol.md) remain the project plan. Arabic work is excluded by request.

## Quick start

Requires Python 3.11+, Poppler (`pdfinfo`, `pdftotext`, `pdftoppm`), and Tesseract. French Tesseract language data (`fra.traineddata`) is required for the scanned PDF.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
mkdir -p data/raw data/ocr
curl -L --fail -o data/raw/constitution_2011_fr_marocma.pdf https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf
curl -L --fail -o data/ocr/fra.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/refs/heads/main/fra.traineddata
# The tested file SHA-256 is ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca.
constitution-evidence ingest
constitution-evidence validate-corpus
constitution-evidence ask 'Que dit l’article 20 sur le droit à la vie ?'
python -m unittest discover -s tests -v
```

For the optional local API: `pip install -e '.[api]'` then `constitution-evidence serve`. Endpoints: `POST /ask`, `GET /sources/{passage_id}`, `GET /health`, `GET /version`.

The downloaded PDF, OCR model, generated text, and runs are ignored by Git. The PDF source, edition, hash, and extraction status are recorded in `data/processed/manifest.json` after ingestion. This project does not claim evaluated factual reliability until the OCR and benchmark have been reviewed. See [scope](docs/project-scope.md), [limitations](docs/limitations.md), and [Gitflow](docs/gitflow.md).

To inspect every French article alongside its PDF pages, run `constitution-evidence audit-corpus` and open `reports/ocr-audit.html`. Verified page corrections can be recorded with hashes and replayed on re-ingestion; see the [OCR review guide](docs/ocr-review.md). The audit and correction workflow do not automatically certify the full corpus.

The provisional 15-question calibration can be rerun with `constitution-evidence evaluate --questions data/annotations/calibration.jsonl --split dev --run-id calibration-bm25 --strategy bm25`. A run saves each question and resumes if its inputs and configuration match. Article recall and MRR are available for these questions; evidence-span metrics need the reviewed annotations described in the [annotation guide](docs/annotation-guide.md).

## Retrieval options

BM25 uses [BM25S](https://github.com/xhluca/bm25s). Install `pip install -e '.[dense]'` to enable CPU dense search with [FastEmbed](https://qdrant.github.io/fastembed/) and [FAISS](https://github.com/facebookresearch/faiss). `--strategy dense`, `hybrid`, and `hybrid-rerank` are available on `ask` and `evaluate`; embedding models download on first use. The dense index is reused only when its model ID and corpus hash match. These candidates have not been selected on a validated benchmark.

The local interface is at `http://127.0.0.1:8000/` after `constitution-evidence serve`. It displays verbatim OCR excerpts, article IDs, and links to the physical PDF page.

## Local open model

The optional [local Qwen setup](docs/local-model.md) uses llama.cpp on `127.0.0.1:8080` and costs no API calls. Run `constitution-evidence ask 'Votre question' --generator local` or select “Résumé local expérimental” in the interface. Exact citations are checked server side; semantic correctness and OCR quality are still unverified. A Gemini adapter remains optional for future comparisons, but no key is needed for the local or extractive modes.

For GPU experiments, use [the Kaggle notebook](notebooks/kaggle_gpu.ipynb). It rebuilds the French corpus from the pinned official PDF, starts an official Qwen3 4B GGUF model with llama.cpp when CUDA is available, and saves raw calibration outputs with model and corpus hashes. It needs a published `develop` branch or an uploaded working tree; it does not perform the missing human review.
