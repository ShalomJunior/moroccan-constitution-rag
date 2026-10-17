# Project log

## 2026-10-17 — Foundation

- Read the 40 day roadmap and technical/evaluation specifications; scoped out all Arabic work by request.
- Acquired two official PDFs. SGG's 65 page PDF yields unreadable text through Poppler; Maroc.ma's 28 page PDF is image only and needs French OCR.
- Implemented page-aware ingestion, article inventory validation, passage offsets and hashes, BM25, extractive evidence display, citation validation, retrieval metrics, CLI, API, and CI.
- Quality gate still pending: human correction of OCR and 180 article/preamble boundary review. Benchmark and model experiments remain pending.

## 2026-10-17 — Retrieval and local generator

- Replaced handwritten BM25 with BM25S and added FastEmbed ONNX + FAISS exact dense search. A 15-question provisional French calibration run gave article Recall@10 of 1.00 BM25, 0.93 dense, and 1.00 hybrid. These are author-written smoke questions and are not a benchmark result.
- Added a local Qwen3 1.7B adapter for llama.cpp with schema-shaped JSON, quote/hash/offset validation, and explicit OCR warning. No legal reviewer or Gemini key is available; final legal fidelity and provider comparisons remain gated.
- Added a `develop` branch and Gitflow guidance. Release branch and tag follow the reviewed corpus and frozen evaluation.
