# French retrieval robustness (provisional development run)

The 15 author-written calibration families were expanded to one direct wording, one paraphrase, and one single-character deletion per family. All 45 questions remain in the `dev` split and reuse the same provisional article labels. The corpus is still unreviewed OCR. These figures describe retrieval against those labels only; they do not measure legal correctness or citation quality.

| Method | Direct Recall@10 | Paraphrase Recall@10 | Typo Recall@10 | Overall Recall@10 |
| --- | ---: | ---: | ---: | ---: |
| BM25S | 15/15 | 15/15 | 14/15 | 44/45 |
| FastEmbed + FAISS | 14/15 | 12/15 | 15/15 | 41/45 |
| Hybrid | 15/15 | 14/15 | 15/15 | 44/45 |

BM25S missed the typo variant in family `cal-07`. Dense missed the paraphrases in `cal-01`, `cal-04`, and `cal-13`, and the direct question in `cal-10`. Hybrid missed the paraphrase in `cal-04`. Its overall recall ties BM25S on this small set, so no improvement is established. Exact per-question hits, code and input hashes, and completion status are stored in the ignored `runs/french-robustness-*` directories; rerun them with `constitution-evidence evaluate --questions data/annotations/robustness_calibration.jsonl --run-id <id> --strategy <method>`.

No gold passage spans exist for these questions, so evidence coverage is unavailable. Revisit this comparison only after corpus and labels are reviewed.
