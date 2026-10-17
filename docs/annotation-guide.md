# French benchmark annotation guide

Each question is one family. Paraphrases of the same intent stay in the same split. Record `question_id`, `family_id`, `split`, `language=fr`, question, category, expected status, required claims, sufficient evidence sets, article IDs and exact spans, forbidden inferences, corpus hash, annotator, and review status. Use `dev`, `validation`, and `test` splits, with planned counts 45/45/90.

Categories: direct lookup, conceptual paraphrase, multiple evidence, false premise, ambiguous, or outside corpus. A passage is relevant only when it supports an element of the answer. For multi article questions, mark all required evidence. An exact citation can still be irrelevant. Mark a source faithful but incomplete answer separately from an unsupported answer.

Answers to ambiguous questions may require clarification. Outside corpus questions require a documented corpus search; retrieval failure alone is not proof of absence. Technical errors are neither correct abstentions nor legal answers. Review at least 20% of families independently if a qualified second reviewer is available. Record disagreements and limits. Do not derive test labels from model outputs.
