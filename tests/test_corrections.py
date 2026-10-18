import tempfile
import unittest
from pathlib import Path
from constitution_evidence.corrections import apply_page_corrections, write_audit_html
from constitution_evidence.ingestion import make_passages, parse_articles, validate_passages
from constitution_evidence.store import digest, write_jsonl

class CorrectionContracts(unittest.TestCase):
    def test_exact_source_anchored_correction_rebuilds_offsets(self):
        pages = ["PRÉAMBULE\nIntro\nArticle premier\nLa liberte de chacun est protegee par cette constitution."]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrections.jsonl"
            correction = {"correction_id": "c1", "page": 1, "source_pdf_sha256": "pdf-hash",
                          "ocr_page_sha256": digest(pages[0]), "old": "liberte", "new": "liberté",
                          "reason": "Compared with PDF page 1", "reviewer": "author"}
            write_jsonl(path, [correction])
            corrected, correction_hash, count = apply_page_corrections(pages, path, "pdf-hash")
            self.assertEqual(count, 1)
            self.assertEqual(correction_hash, digest(path.read_bytes()))
            self.assertIn("liberté", corrected[0])
            self.assertNotIn("liberté", pages[0])
            articles = parse_articles(corrected)
            passages = make_passages(articles)
            validate_passages(articles, passages)
            self.assertIn("liberté", passages[1]["canonical_text"])
            with self.assertRaisesRegex(ValueError, "Source PDF or OCR page changed"):
                apply_page_corrections(pages, path, "other-pdf")
            correction["old"] = "e"
            write_jsonl(path, [correction])
            with self.assertRaisesRegex(ValueError, "matched [0-9]+ times"):
                apply_page_corrections(pages, path, "pdf-hash")

    def test_audit_escapes_ocr_text_and_keeps_status(self):
        articles = [{"article_number": 1, "page_spans": [3], "canonical_text": "<script>unsafe</script>",
                     "text_hash": "abc"}]
        manifest = {"source_url": "https://example.org/source.pdf", "review_status": "unreviewed_ocr",
                    "corpus_hash": "hash", "pdf_sha256": "pdf-hash"}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.html"
            result = write_audit_html(articles, manifest, output)
            content = output.read_text()
            self.assertIn("&lt;script&gt;unsafe&lt;/script&gt;", content)
            self.assertNotIn("<script>unsafe</script>", content)
            self.assertIn("source.pdf#page=3", content)
            self.assertEqual(result["review_status"], "unreviewed_ocr")

if __name__ == "__main__":
    unittest.main()
