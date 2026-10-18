import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from constitution_evidence.review import create_review_template, certify_corpus
from constitution_evidence.store import digest, read_jsonl, write_jsonl


class CorpusReviewTests(unittest.TestCase):
    def test_signoff_requires_all_current_units_and_refuses_stale_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            articles_path, manifest_path, review_path = (root / name for name in
                                                       ('articles.jsonl', 'manifest.json', 'review.jsonl'))
            articles = [{'article_number': i, 'text_hash': f'h{i}', 'page_spans': [1]}
                        for i in range(181)]
            write_jsonl(articles_path, articles)
            manifest_path.write_text(json.dumps({'article_count': 180, 'corpus_hash': digest(articles_path.read_bytes()),
                                                 'pdf_sha256': 'pdf', 'review_status': 'unreviewed_ocr'}))
            create_review_template(articles_path, manifest_path, review_path)
            with self.assertRaisesRegex(ValueError, 'unit 0'):
                certify_corpus(articles_path, manifest_path, review_path)
            rows = read_jsonl(review_path)
            for row in rows:
                row.update(pdf_checked=True, reviewer='Human reviewer',
                           reviewed_at=datetime.now(timezone.utc).isoformat())
            write_jsonl(review_path, rows)
            result = certify_corpus(articles_path, manifest_path, review_path)
            self.assertEqual(result['status'], 'reviewed')
            self.assertEqual(json.loads(manifest_path.read_text())['reviewed_units'], 181)
            rows[23]['article_text_hash'] = 'old text'
            write_jsonl(review_path, rows)
            with self.assertRaisesRegex(ValueError, 'unit 23'):
                certify_corpus(articles_path, manifest_path, review_path)


if __name__ == '__main__':
    unittest.main()
