# PDF diagnostics — 2026-10-17

The SGG French 2011 PDF has 65 pages and a text layer, but `pdftotext -layout` returns encoded glyphs such as `5R\\DXPH`; it is unusable as a direct canonical text. The Maroc.ma 2011 bulletin PDF has 28 physical pages and no extractable text. French Tesseract OCR at 170 dpi produced 28 page files. The first constitutional text is on physical page 3, and article 180 is on physical page 28. Editorial text after article 180 is excluded.

The parser finds all 180 article headings in sequence after allowing observed OCR heading errors (`Artiele` and stray punctuation). It also extracts the preamble. This proved inventory, not accurate transcription. At the time of this diagnostic, sample defects included displaced word order in Article 1 and a line from Article 179 moved into Article 180. The project owner later compared all French units with the PDF, and the corrected corpus is documented in [the current reconciliation](external-review-reconciliation.md).

Source hashes and URLs are in [the source manifest](../data/manifests/sources.json). The extraction command and parser are in `src/constitution_evidence/ingestion.py`. The local run used Tesseract 5.3.4, Poppler 24.02.0, and French traineddata SHA-256 `ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca`.
