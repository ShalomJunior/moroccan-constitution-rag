# Short French dialogue and operations

`POST /ask` accepts up to three `history` entries. Each entry contains up to five article numbers, never an earlier model answer. Example:

```json
{"question":"Que prévoit cet article ?","history":[{"article_numbers":[20]}],"generator":"extractive"}
```

The API reformulates `cet article`, `ce même article`, and `l'article précédent` only when the most recent entry identifies exactly one article. If there is no unique article, it returns `needs_clarification` and asks for its number. A question explicitly naming an article takes precedence over history. Every resolved follow-up runs retrieval again, and the answer contains `dialogue.resolved_question` and `dialogue.next_article_numbers`. The browser keeps this bounded history in memory and offers **Nouveau sujet** to clear it; the server holds no session state. The 15 development dialogue fixtures in `data/annotations/dialogue_calibration.jsonl` are provisional parser checks, not a user study.

`POST /ask`, `GET /sources/{id}`, `GET /health`, and `GET /version` have input limits and offline contract tests. The interface presents an excerpt first, then loads the exact passage when its citation is opened and links to the PDF page. A missing source returns 404; unavailable corpus or model returns 503. An empty retrieval result yields `insufficient_evidence` in both answer modes.

Completed requests emit a structured log with request ID, corpus hash, method, status, source count, call count, provider attempts, token usage when supplied, and elapsed milliseconds. It excludes the question, passage text, and credentials. The local model adapter retries transient connection failures or HTTP 429/502/503/504 once; validation failures and other HTTP statuses are not retried. Retrieval evaluation saves each question atomically and resumes only when input and code hashes match. The active corpus and dense index are keyed by corpus content hashes.
