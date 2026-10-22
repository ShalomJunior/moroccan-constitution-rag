import tempfile
import unittest
from pathlib import Path

from constitution_evidence.question_packet import write_question_packet
from constitution_evidence.store import write_jsonl


class QuestionPacketTests(unittest.TestCase):
    def test_packet_links_candidate_source_without_promoting_label(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions, articles, passages, output = (root / name for name in
                ("questions.jsonl", "articles.jsonl", "passages.jsonl", "packet.md"))
            write_jsonl(questions, [{"question_id": "q1", "split": "dev", "question": "Que dit l'article 20 ?",
                                     "candidate_articles": [20], "review_status": "author_provisional"}])
            write_jsonl(articles, [{"article_number": 20, "canonical_text": "La loi protège ce droit.",
                                    "page_spans": [7]}])
            write_jsonl(passages, [{"article_number": 20, "passage_id": "art-20:p-1",
                                    "canonical_text": "La loi protège ce droit.", "page_spans": [7]}])
            result = write_question_packet(questions, articles, passages, "https://example.org/pdf", output)
            packet = output.read_text()
            self.assertEqual(result["questions"], 1)
            self.assertIn("author_provisional", packet)
            self.assertIn("https://example.org/pdf#page=7", packet)
            self.assertIn("art-20:p-1", packet)
            self.assertNotIn('"review_status":"reviewed"', packet)


if __name__ == "__main__":
    unittest.main()
