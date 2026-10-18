# Release gate, reserved test, and human judgments (J34–J38)

## J34: latency and variation

`constitution-evidence bench-retrieval --run-id NAME` records index build time, first-query and concurrent warm-query timings, errors, hardware class, input hashes, and every observation under ignored `runs/NAME/latency.json`. It measures retrieval only. The fixed five-question development subset in `configs/latency_questions.json` can be used with `bench-generation --run-id NAME` when a local Qwen server is available; it makes exactly three calls per question and stores response hashes, token usage when available, failures, and latency. Its run ID must be new. No live generation variation has been measured yet.

On this machine, a provisional BM25S run over 15 author-written dev questions had 200.758 ms index build time, 0.284 ms median first-query latency (15 calls), and 0.952 ms median warm latency at concurrency two (45 calls), with zero errors. Warm requests run concurrently, so these two phases are not a direct cache speedup estimate. These numbers are CPU-only retrieval timings on Python 3.12.3, x86_64 Linux, over unreviewed OCR. They exclude model generation, network, and hardware cost. The detailed run is `runs/latency-bm25-20261018/latency.json` and can be recreated from the tracked questions.

## J35: release candidate

`constitution-evidence release-readiness` writes a blocked or ready manifest under `runs/release-candidate/manifest.json`. It requires reviewed corpus and labels (45 dev, 45 validation, 90 test families), a validation selection, three final system configs, a clean Git revision, `uv.lock`, and the prewritten `configs/analysis_plan.json`. It records hashes for all of these. The current manifest is blocked; no release tag is warranted. The three systems remain full text, BM25 RAG, and the selected pipeline, but their model and prompt versions are not fixed yet.

## J36: reserved execution

`test-preflight` and `evaluate --split test` refuse to open reserved questions until a ready release manifest matches the current corpus, questions, code revision, selection, system config, analysis plan, and dependency lock. `run_reserved_test` is the saved-run library interface for three fixed system adapters. It writes one atomic answer row per question per system and resumes without duplicate calls if interrupted. Each row stores the answer, context passage IDs, error, and elapsed time. Technical failures remain visible in the run rather than becoming abstentions. The current release gate correctly rejects the reserved test.

## J37–J38: blind review and statistics

After all three reserved answer files exist, `blind-packets` creates shuffled `packets.jsonl` and a separate `private_mapping.jsonl` under a new output directory. Only the packets go to annotators. Each packet exposes the question, response, and source links while stripping system/model/retriever metadata. The private mapping links the blind ID back to a system. Packet creation refuses incomplete runs, duplicate question IDs, unreviewed questions, and an existing output directory.

The finalized judgments JSONL needs one row per blind ID with `finalized: true` and Boolean `decision_ok`, `faithful`, `complete`, `citations_ok`, and `unsupported_or_incorrect`. Use a reason and annotation time in extra fields for audit; disagreements must be resolved before marking finalized. `score-judgments --mapping PATH --judgments PATH` computes strict success over all questions (technical failures count as failures), coverage, risk among substantive answers, technical-error counts, elapsed time, optional risk–coverage curves when confidence scores exist, and 2,000 family-paired bootstrap replications with the fixed seed. It rejects missing or unfinished labels. No human judgments exist yet, so there are no final scores or intervals to publish.
