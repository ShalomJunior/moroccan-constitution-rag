# Project log

## 2026-10-18 — Report and offline reproduction

- Added a development technical report with five saved-run retrieval failure cases, including cases where BM25S retrieves a provisional label that dense or hybrid misses. The report does not present unreviewed OCR or author-written labels as final legal evidence.
- Added a data card, five-minute demo script, reproduction guide, and an explicit J41–J50 extension gate. No `v1.0` or `v2` tag was created because release prerequisites are incomplete.
- Added offline recomputation of every saved retrieval metric from question labels, corpus passages, and saved hits; it rejects tampering. Added a tracked-file publication audit to CI. On the current local corpus, BM25S and hybrid saved runs reproduced, and 41 offline tests passed.

## 2026-10-18 — Latency, release gates, and blind review tooling

- Measured provisional BM25S retrieval on 15 dev questions: 200.758 ms index build, 0.284 ms median first-query latency, 0.952 ms median concurrent warm latency, 0 errors across 60 calls. No model or answer-quality conclusion follows.
- Added fixed-subset triple-generation variability tooling, a release manifest with frozen input/code/config hashes and analysis plan, and a reserved-test runner that resumes per question. The current corpus and benchmark fail the release gate, so no release candidate or final test was run.
- Added blind answer packets, private system mapping, finalized human-judgment validation, risk/coverage and strict-success summaries, and family-paired bootstrap intervals. These have synthetic tests only; no human judgments or final statistics exist.

## 2026-10-18 — Demo controls and experiment gates

- Added bounded concurrent local-model calls, input limits, safety fixtures, and a short demo threat model. Structural citation checks reject forged quotes; semantic support remains unverified.
- CI now installs from the committed uv lock. Local lock validation and 35 offline tests passed. A fresh-clone installation and volunteer usability tests remain pending.
- Added paired saved-run comparisons, a reviewed-validation retrieval selection policy, and a resumable oracle generator that never passes answer labels to the model. The current provisional labels correctly fail the validation and oracle gates; no final selection or oracle result is claimed.

## 2026-10-18 — French robustness and short dialogue

- Added 45 provisional French query variants across 15 development families and compared BM25S, FastEmbed + FAISS, and hybrid retrieval. Recall@10 was 44/45, 41/45, and 44/45 respectively; see `reports/french-robustness.md` for variant and family failures. These are author labels over unreviewed OCR, not release metrics.
- Added stateless, bounded article follow-ups and clarification, an in-memory browser reset, offline dialogue fixtures, and fresh retrieval for every resolved turn. The model never receives previous answer text as source material.
- Added request IDs and structured completion logs, one retry for transient local model failures, and a clean abstention for empty retrieval in local mode. Full end-to-end Qwen operation and legal review are still pending.

## 2026-10-17 — Foundation

- Read the 40 day roadmap and technical/evaluation specifications; scoped out all Arabic work by request.
- Acquired two official PDFs. SGG's 65 page PDF yields unreadable text through Poppler; Maroc.ma's 28 page PDF is image only and needs French OCR.
- Implemented page-aware ingestion, article inventory validation, passage offsets and hashes, BM25, extractive evidence display, citation validation, retrieval metrics, CLI, API, and CI.
- Quality gate still pending: human correction of OCR and 180 article/preamble boundary review. Benchmark and model experiments remain pending.

## 2026-10-17 — Retrieval and local generator

- Replaced handwritten BM25 with BM25S and added FastEmbed ONNX + FAISS exact dense search. A 15-question provisional French calibration run gave article Recall@10 of 1.00 BM25, 0.93 dense, and 1.00 hybrid. These are author-written smoke questions and are not a benchmark result.
- Added a local Qwen3 1.7B adapter for llama.cpp with schema-shaped JSON, quote/hash/offset validation, and explicit OCR warning. No legal reviewer or Gemini key is available; final legal fidelity and provider comparisons remain gated.
- Added a `develop` branch and Gitflow guidance. Release branch and tag follow the reviewed corpus and frozen evaluation.

## 2026-10-17 — Evaluation contract and recovery

- Separated article recall/MRR from evidence-span coverage. The 15-question provisional calibration lacks reviewed spans, so evidence coverage is now reported as unavailable rather than inferred from article matches.
- Added exact passage-span labels and alternative sufficient evidence sets to the evaluation contract. Run artifacts now save after each question and resume only with matching inputs, configuration, and evaluator code. The run report states whether all planned questions are present.
- Eight offline contract tests pass. The corpus remains `unreviewed_ocr`; no final benchmark or legal reliability claim follows from these checks.
- Expanded the Kaggle Qwen4B notebook to save and resume all 15 provisional generation questions, with exact contexts, model/corpus hashes, prompt version, elapsed time, and errors. Kaggle execution is still pending.

## 2026-10-17 — OCR review workflow

- Added a static report covering the preamble and all 180 articles, with links to the PDF pages and raw OCR pages. It is an inspection aid, not a review verdict.
- Added exact OCR-page corrections anchored to the source PDF and raw page hashes. Re-ingestion applies them before article parsing, then rebuilds passage offsets and records the correction file hash. No corrections have been asserted without checking the PDF.
- The corpus still has `unreviewed_ocr` status and needs full human comparison with the PDF before release.

## 2026-10-17 — Multi-article answers and API retrieval

- Explicit article lists now retrieve passages across all named articles, and preamble lookup is direct. Hybrid search postpones dense model loading until a query needs it.
- The API and interface expose BM25, dense, hybrid, and hybrid plus reranking. The interface opens the exact passage behind each citation. Real BM25 and hybrid smoke queries returned both articles 20 and 21 for a two-article question.
- This improves the answer path but does not establish semantic support or legal completeness on the unreviewed corpus.

## 2026-10-17 — Explicit reference expansion

- Added an optional one-hop reference graph from article text, with exact quote offsets and target inventory checks. A query can reserve one result for an article cited inside a retrieved passage, without recursive expansion.
- Exposed the option in the CLI, API, and interface, and attached reference provenance to returned sources. On the current corpus, a query for article 51 returned article 96 via the explicit text “articles 96, 97 et 98”.
- The graph is extracted from unreviewed OCR. It is an experimental retrieval option, not a measured improvement or a verified legal interpretation.

## 2026-10-18 — Bounded multi-evidence search

- Added an optional search plan with the original question and at most two focused subquestions. Explicit multi-article questions plan locally; conceptual questions use the loopback Qwen server with JSON validation.
- Search results are merged with deduplication and trace the questions, candidate IDs, selected IDs, actual context IDs, call counts, token usage when returned, and elapsed time. The original question is always searched, and no recursive agent loop is used.
- A local explicit-article smoke query retrieved passages from articles 20 and 21 in three bounded searches. Conceptual Qwen planning has contract tests but has not been run against a live model; no quality improvement is claimed.
