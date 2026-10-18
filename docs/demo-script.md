# Five-minute demonstration script (development build)

**0:00–0:40 — Scope.** Show the institutional French PDF link and the project owner's single-reviewer `reviewed` corpus status. State that the application finds inspectable excerpts; it does not validate a legal conclusion. Mention that Arabic work is excluded by project choice.

**0:40–1:30 — Direct lookup.** Start `constitution-evidence serve`, ask “Que dit l’article 20 sur le droit à la vie ?”, open the citation, then the linked PDF page. Point out the exact passage text and partial-answer warning.

**1:30–2:15 — Multiple sources.** Ask “Que disent les articles 20 et 21 ?” and inspect one citation from each article. Toggle bounded decomposition only if explaining its extra searches and trace; do not imply it improved quality without reviewed evidence.

**2:15–2:55 — Follow-up.** Ask “Que prévoit cet article ?” after a single-article question, then press **Nouveau sujet** and repeat it to show clarification. Explain that only article numbers are carried between turns and retrieval runs again.

**2:55–3:40 — Search methods.** Show the current 15-question retrieval results in `reports/external-review-reconciliation.md`. State that the questions and article labels remain provisional and cannot establish answer accuracy.

**3:40–4:25 — Reproduction and gates.** Run `constitution-evidence reproduce-retrieval french-robustness-bm25 french-robustness-hybrid`, then `constitution-evidence release-readiness`. The first recalculates saved retrieval scores without an API; the second is blocked because review and final systems are missing. Do not show a `v1.0` badge or final score.

**4:25–5:00 — Limits and next work.** Summarize PDF review, 180-family annotations, validation selection, live Qwen generation study, final test, and blind judgments. A citation can be exact while the surrounding model claim is unsupported. Invite the audience to inspect the PDF page rather than treating the tool as legal advice.
