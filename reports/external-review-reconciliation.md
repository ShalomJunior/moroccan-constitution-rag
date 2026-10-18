# French OCR review reconciliation — 2026-10-18

The project owner reported checking the complete 28-page French PDF and supplied observations for the preamble and Articles 1–180. The observations have SHA-256 `651c8af7dc19143c1686bb23a3a6f90b8df2beb1870869ca6558e163adfb2fa1`; the raw notes are kept outside the public release. This is one person's OCR comparison, not an independent legal assessment.

The [correction journal](../data/annotations/ocr-corrections.jsonl) now has 309 exact source-page edits: the earlier Article 27 correction and 308 edits from this review. Each edit is anchored to the source PDF SHA-256 `4101d45b4733a6b36eee77bd9ef4175b23160103089b003b13907e8b6d59333d` and its raw OCR page hash. Edits include word and punctuation repairs, missing list markers, reordered lines, removal of page headers and section titles from article text, and relocation of the misplaced Article 179 clause from Article 180. The parser now joins OCR blank-line breaks that split a sentence while preserving article text and exact passage offsets.

The active local corpus contains 181 units and 483 passages. Its article hash is `c319ecb4cabe0eaafc3de18779cc210ec8fa83cffbaeb2259393073e9fb4901c`; its passages hash is `a4abf1b043a72c18d6dcc740f3f3ebbbc1a29aeebf0eedb8c1264d0793c5079c`. The [review journal](../data/annotations/corpus-review.jsonl) ties all 181 units to their corrected article hashes and records the owner's self-attested PDF comparison. `certify-corpus` passed and the active manifest says `reviewed`. Re-ingestion resets this flag until certification is replayed against the same hashes. The automated [OCR risk scan](ocr-risk-audit.md) has zero pattern matches; that is not an estimate of residual error.

## Development checks on this corpus

The 15 author-written development questions have provisional article labels and no reviewed evidence spans. These numbers test search and structural output only.

| Retrieval | Article recall@10 | Article MRR@10 |
| --- | ---: | ---: |
| BM25S | 15/15 | 0.967 |
| FastEmbed + FAISS | 15/15 | 0.808 |
| Hybrid | 15/15 | 0.967 |

Saved local runs are `runs/external-review-final-bm25`, `runs/external-review-final-dense`, and `runs/external-review-final-hybrid`. BM25S remains the default. The Groq development run `runs/external-review-final-groq` used `openai/gpt-oss-20b` and BM25 context. Fourteen of 15 responses were structurally valid and passed exact passage ID, hash, offset, and quote checks on replay; one (`cal-13`) was rejected after a citation quote mismatch. The successful responses reported 13,153 tokens; failed requests may consume unreported tokens. Median request time was 0.698 seconds across the 15 saved calls. The owner's subsequent answer judgments and a second development run are summarized in [the answer review](development-answer-review.md).

## Remaining release gate

`release-readiness` now passes the corpus review condition but remains blocked: the planned 45 development, 45 validation, and 90 reserved-test families with reviewed labels are absent; validation selection and three frozen system configurations are absent; the working tree is uncommitted. Historical OCR-dependent runs and reports use different hashes and are not current evidence. No final answer-quality or legal-reliability claim follows from this review alone.

The two completed development reviews are not a substitute for the planned benchmark or a legal reliability study.
