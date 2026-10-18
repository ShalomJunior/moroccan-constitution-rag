# Project log

## 2026-10-18 — Complete French OCR review observations integrated

- The project owner supplied observations after comparing the preamble and Articles 1–180 against the French PDF and identified themselves as the reviewer. Preserved the observations with SHA-256 `651c8af7dc19143c1686bb23a3a6f90b8df2beb1870869ca6558e163adfb2fa1`.
- Applied 308 new PDF- and raw-page-hash-anchored corrections, for 309 total including Article 27. Repaired words, punctuation, list markers, reordered lines, section-heading leakage, and the displaced Article 179 clause. Reflowed OCR blank-line breaks inside sentences without changing article text.
- Rebuilt 181 French units and 483 passages. Article hash `c319ecb4cabe0eaafc3de18779cc210ec8fa83cffbaeb2259393073e9fb4901c`; passage hash `a4abf1b043a72c18d6dcc740f3f3ebbbc1a29aeebf0eedb8c1264d0793c5079c`. The owner's self-attested single-reviewer journal passed `certify-corpus`; active status is `reviewed`.
- On 15 provisional dev questions, BM25S, dense, and hybrid each found the labeled article in 15/15 top-ten searches. Groq returned 14 structurally valid answers and one rejected quote mismatch. These results do not assess semantic support. The release gate is still blocked by the missing reviewed benchmark, validation selection, final system configs, and clean revision. See `reports/external-review-reconciliation.md`.
- Prepared an ignored local development answer-review packet with the 15 saved Groq outcomes and source PDF links. Human judgments remain blank.

## 2026-10-18 — Targeted OCR triage and corrected-corpus calibration

- Added an automated OCR risk audit against the active manifest and validated inventory. It flags three possible fused-apostrophe lines for PDF inspection; these are candidates, not an accuracy estimate. Article 27 remains the sole recorded page correction.
- Recomputed the 15 provisional dev questions after that correction. BM25S, dense, and hybrid article recall@10 were 15/15, 14/15, and 15/15 respectively; evidence-span metrics remain unavailable. BM25S stays the default.
- Added resumable, hash-anchored Groq calibration with bounded citation-repair retry. The repaired ranked-hit run returned 15/15 structurally valid responses, including three abstentions caused by missing article openings in context.
- Added budgeted opening paragraphs for retrieved articles to the generator context. A fresh Groq run changed those three abstentions to cited partial answers; 14/15 responses passed structural checks and one quote mismatch was rejected. These stochastic runs do not establish semantic or legal quality.

## 2026-10-18 — Targeted Article 27 OCR correction

- The project owner supplied the Article 27 transcription from PDF page 7. Recorded one exact raw-page replacement in `data/annotations/ocr-corrections.jsonl`, anchored to the PDF and raw OCR page hashes. Re-ingestion changed only Article 27, retained its two PDF paragraphs, and produced 632 passages. `validate-corpus` and all 49 offline tests pass.
- The active corpus remains `unreviewed_ocr`; a targeted correction does not certify the remaining 180 French units. The earlier Kaggle calibration uses the previous corpus hash and is retained as a historical provisional run.

## 2026-10-18 — Report and offline reproduction

- Added a development technical report with five saved-run retrieval failure cases, including cases where BM25S retrieves a provisional label that dense or hybrid misses. The report does not present unreviewed OCR or author-written labels as final legal evidence.
- Added a data card, five-minute demo script, reproduction guide, and an explicit J41–J50 extension gate. No `v1.0` or `v2` tag was created because release prerequisites are incomplete.
- Added offline recomputation of every saved retrieval metric from question labels, corpus passages, and saved hits; it rejects tampering. Added a tracked-file publication audit to CI. On the current local corpus, BM25S and hybrid saved runs reproduced. A committed source archive passed all 41 offline tests using the existing environment; a fresh dependency install is still pending.

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

## 2026-10-18 — Development answer review and citation repair

- Archived the owner's completed 15-question Groq answer review and structured each judgment against the original run. Seven answers met all four human criteria; eight had at least one failure.
- Added multiple exact citations per claim, nearby paragraph context, explicit completeness instructions, and normalization of spurious limitation labels. Tests cover a claim citing an article introduction and a list item, plus inclusion of a following limiting paragraph.
- Ran a separate 15-question Groq development calibration with the revised code: 13 structured answers and two exact-citation rejections. Some prior failures improved, but answers to `cal-11`, `cal-12` and `cal-15` still omit relevant content. The new run has a blank human review packet; no post-change human success rate is claimed.
- The project owner completed the v2 review: 8/15 answers met every criterion, compared with 7/15 on v1. Seven v2 failures remain, including semantic extrapolation, omissions, and quote mismatch. We archived the judgments and ended this manual calibration loop.
- Added a locked CPU Docker Compose deployment for the browser, BM25, and optional Groq. The container mounts the processed corpus read-only and publishes only on host loopback. Built the image and verified `/health` and an extractive article 20 question against the active corpus; then stopped the test container. CI now checks Compose syntax.
- Extended the Docker profile with the locked dense extra and a persistent writable model/index volume. Redirected FastEmbed and Hugging Face caches into that volume to preserve a read-only root filesystem. Verified real Docker requests for dense, hybrid, and hybrid plus reranking all return 200 after first-use model downloads. Added `/capabilities` so the browser disables local Qwen generation when no separate server is reachable.
