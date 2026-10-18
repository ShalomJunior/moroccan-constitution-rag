# Development experiments and release gates

## Saved-run comparison (J31)

Use `constitution-evidence compare-runs RUN_A RUN_B` for a paired development ablation. The command rejects incomplete runs, mismatched question IDs, splits, corpus hashes, article cutoff, or context budgets, and refuses the reserved test split. It reports per-question deltas and the number of evaluable questions for each metric. The existing 45-question French robustness runs support a retrieval-method comparison only; they contain no reviewed evidence spans or answer judgments.

For the provisional BM25S and hybrid runs, Recall@10 is tied at 44/45. Hybrid minus BM25S mean MRR@10 is +0.003704 over 45 variants. Complete evidence and context evidence coverage have no labels (`n=0`). This does not select a final method. Run artifacts are in ignored `runs/french-robustness-*` directories and can be regenerated from the tracked question file.

The remaining ingestion, chunking, reranking, reference expansion, decomposition, and verification ablations need comparable runs and, for evidence or answer claims, reviewed labels. Do one variable at a time and retain negative runs.

## Validation selection (J32)

`constitution-evidence select-validation --questions PATH RUN_ID [RUN_ID ...]` applies the tracked [selection policy](../configs/selection_policy.json) to complete validation runs. It requires at least 45 distinct reviewed families. Answerable questions need sufficient evidence sets and non-null complete evidence scores; ambiguous and out-of-scope questions remain in the inventory but are excluded from this retrieval metric. The primary criterion is complete evidence; MRR breaks ties. It refuses provisional or incomplete data and never opens test runs. Answer risk, coverage, and an abstention threshold require reviewed response judgments and are therefore outside this retrieval-only choice.

## Oracle context (J33)

`constitution-evidence oracle-run --questions PATH --split dev --run-id NAME` sends the first reviewed sufficient evidence set for each question to the local model. It requires matching corpus hashes, exact current passage offsets, and reviewed dev or validation labels. Only the question text and passage records reach the generator; required claims, statuses, and answer annotations stay outside the prompt. The run writes a manifest and each answer or error after every question, and resumes only with matching questions, corpus, model ID, and prompt hash. Oracle responses are diagnostic and cannot be shown as product performance. This path has offline tests but cannot run against the present provisional annotations.
