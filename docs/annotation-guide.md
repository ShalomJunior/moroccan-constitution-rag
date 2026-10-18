# French benchmark annotation guide

Each question is one family. Paraphrases of the same intent stay in the same split. Record `question_id`, `family_id`, `split`, `language=fr`, question, category, expected status, required claims, sufficient evidence sets, article IDs and exact spans, forbidden inferences, corpus hash, annotator, and review status. Use `dev`, `validation`, and `test` splits, with planned counts 45/45/90.

Categories: direct lookup, conceptual paraphrase, multiple evidence, false premise, ambiguous, or outside corpus. A passage is relevant only when it supports an element of the answer. For multi article questions, mark all required evidence. An exact citation can still be irrelevant. Mark a source faithful but incomplete answer separately from an unsupported answer.

Answers to ambiguous questions may require clarification. Outside corpus questions require a documented corpus search; retrieval failure alone is not proof of absence. Technical errors are neither correct abstentions nor legal answers. Review at least 20% of families independently if a qualified second reviewer is available. Record disagreements and limits. Do not derive test labels from model outputs.

## Span labels for retrieval evaluation

`relevant_articles` alone supports article recall and MRR. It does **not** establish complete evidence. For reviewed questions, record exact canonical passage offsets in `relevant_spans`. Each alternative sufficient set belongs in `acceptable_evidence_sets`; all spans within one set are jointly required. For example:

```json
{
  "relevant_articles": [20, 21],
  "relevant_spans": [
    {"passage_id": "ma-constitution-2011:fr:art-20:p-1", "char_start": 0, "char_end": 25},
    {"passage_id": "ma-constitution-2011:fr:art-21:p-1", "char_start": 0, "char_end": 32}
  ],
  "acceptable_evidence_sets": [[
    {"passage_id": "ma-constitution-2011:fr:art-20:p-1", "char_start": 0, "char_end": 25},
    {"passage_id": "ma-constitution-2011:fr:art-21:p-1", "char_start": 0, "char_end": 32}
  ]]
}
```

These offsets are illustrative; copy the actual offsets from the **reviewed** corpus. A span is covered when its exact passage is retrieved and its offsets remain valid. The retrieval report measures article-level `Recall@k` and `MRR@k`, span recall among passages from the first `k` distinct articles, complete coverage of at least one sufficient evidence set, and span coverage in the context selected for generation. Unannotated evidence metrics are `null`, never inferred from article matches. Re-annotate or explicitly migrate offsets when the corpus hash changes.

Run a provisional retrieval experiment with `constitution-evidence evaluate --questions data/annotations/calibration.jsonl --split dev --run-id my-run --strategy bm25`. It saves each question before moving to the next and resumes with the same run ID only when inputs, configuration, and evaluator code hashes match. Use `constitution-evidence report --run-id my-run` to recalculate aggregates. These calibration labels are author-provisional, so the resulting scores are not final benchmark results.
