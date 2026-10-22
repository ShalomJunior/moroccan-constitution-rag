# Project scope — Constitution Evidence

**Corpus.** The French text of Morocco's 2011 Constitution, from the [Maroc.ma institutional PDF](https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf). The edition is 2011; the URL's 2024 upload directory is not a new edition. The SGG PDF was inspected too, but its text extraction is unreadable. The downloaded PDFs are kept locally and excluded from Git pending redistribution review.

**Users and questions.** A reader asks in French for a constitutional provision, a principle, or passages relevant to a comparison. The tool gives source excerpts and physical PDF pages. It does not determine current case law, implementing laws, litigation outcomes, or legal advice.

**Language.** French only. Arabic ingestion, alignment, questions, interface, and evaluation are outside the retained scope.

**Success criteria.** All 180 numbered articles are present in order, plus a complete preamble; every passage has stable offsets and a source hash; citation validation rejects invented or stale quotes; retrieval is evaluated on annotated French questions with split isolation; an offline reproduction and three comparable systems are reported before claiming evaluation success. OCR errors must be reviewed before substantive legal fidelity claims.

**Budget.** Offline ingestion, retrieval, and extractive display have no API charge. The optional model runs need an explicit key, model, price check, and spend cap. No paid calls are triggered by setup.

**Current state.** Version `1.0.0` packages the French application and corrected corpus workflow with a completed 45/45/90-question benchmark, validation selection, frozen three-system Kaggle test, and owner-provided blind answer judgments. The [final evaluation](../reports/final-evaluation.md) reports measured errors and does not establish general legal reliability or evaluate the application's Groq mode.
