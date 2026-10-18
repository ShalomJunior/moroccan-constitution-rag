# Bounded multi-evidence search

Enable `--decompose` on `constitution-evidence ask`, or select “Décomposer la recherche” in the interface. The original question is always searched. At most two additional questions are searched, for at most three retrieval calls total. The final context is capped by the same passage budget used by the selected answer mode. The response includes the subquestions, call count, model usage when available, candidate IDs, selected IDs, and context IDs.

When the question explicitly names at least two articles, the extra searches are article-specific and need no model. For other questions, the local Qwen server proposes one or two subquestions through a constrained JSON interface. The server must run on loopback; see [local model setup](local-model.md). If it is unavailable, the request fails as a provider error rather than pretending to abstain on legal grounds. No paid API is needed.

The planner's wording is **not verified to preserve the user's intent**. Keeping the original query and showing every subquestion reduces the chance of silent drift but does not prove semantic equivalence. The merged evidence still needs review for completeness and relevance. This is an experimental retrieval variant; no measured advantage over a single search has been established on reviewed multi-evidence questions.
