# Limitations and release gates

The source PDF is an image scan. OCR contains visible errors (for example, spelling mistakes in article 23 on the first sample), so the generated text is not yet a reviewed legal transcription. Article count alone does not validate article boundaries or substantive accuracy. The current offline answer returns verbatim excerpts and marks them `partially_answered`; lexical relevance is not semantic support. Do not claim that a displayed excerpt fully answers a question.

No French 180-family benchmark, human judgments, validated reranker study, local model quality study, or risk/coverage study is complete. Dense retrieval and a Gemini adapter are implemented but have not been selected on a reviewed benchmark. A final comparison against full text requires model access, a measured token budget, and a frozen test set. The release gate is a reviewed corpus plus documented evaluation, not simply a passing unit test.
