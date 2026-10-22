import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from constitution_evidence.api import _load_articles, article, articles
from constitution_evidence.store import digest, write_jsonl


class ArticleBrowserTests(unittest.TestCase):
    def test_article_index_refuses_changed_canonical_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "articles.jsonl"
            write_jsonl(path, [{"article_number": 20, "canonical_text": "La loi protège ce droit.",
                                "page_spans": [7]}])
            manifest = {"corpus_hash": digest(path.read_bytes()), "edition_id": "2011-fr",
                        "source_url": "https://example.org/pdf"}
            with patch("constitution_evidence.api.corpus_paths", return_value=(path, None, None)):
                with patch("constitution_evidence.api._load_corpus", return_value=(None, manifest, {})):
                    self.assertIn(20, _load_articles.__wrapped__("manifest-hash")[1])
                    path.write_text(path.read_text().replace("protège", "ignore"))
                    with self.assertRaisesRegex(ValueError, "Articles hash"):
                        _load_articles.__wrapped__("manifest-hash")

    def test_api_lists_and_opens_preamble_and_article(self):
        records = {0: {"article_number": 0, "canonical_text": "Préambule.", "page_spans": [3]},
                   20: {"article_number": 20, "canonical_text": "La loi protège ce droit.", "page_spans": [7]}}
        manifest = {"edition_id": "2011-fr", "review_status": "reviewed",
                    "source_url": "https://example.org/pdf"}
        with patch("constitution_evidence.api.corpus_paths", return_value=(None, None, Path(__file__))):
            with patch("constitution_evidence.api._load_articles", return_value=(manifest, records)):
                self.assertEqual([row["article_number"] for row in articles()["articles"]], [0, 20])
                self.assertEqual(article(0)["canonical_text"], "Préambule.")
                self.assertEqual(article(20)["page_spans"], [7])
                with self.assertRaises(HTTPException) as raised:
                    article(21)
                self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
