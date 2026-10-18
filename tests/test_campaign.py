import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constitution_evidence.campaign import build_runners, prompt_hash
from constitution_evidence.generation import GenerationError
from constitution_evidence.local_generation import LocalGenerator
from constitution_evidence.store import digest, write_jsonl


class CampaignTests(unittest.TestCase):
    def test_fulltext_preflight_refuses_small_context_before_completion(self):
        passage = {"passage_id": "p1", "canonical_text": "Constitution", "text_hash": "h",
                   "article_number": 1, "page_spans": [1]}
        responses = [
            {"default_generation_settings": {"n_ctx": 512}},
            {"prompt": "rendered chat template"},
            {"tokens": list(range(100))},
        ]
        paths = []
        def open_fake(request, timeout):
            paths.append(request.full_url)
            return io.BytesIO(json.dumps(responses.pop(0)).encode())
        with patch("constitution_evidence.local_generation.urlopen", side_effect=open_fake):
            with self.assertRaisesRegex(GenerationError, "budget_exceeded"):
                LocalGenerator(require_token_preflight=True).generate("Question ?", [passage], {})
        self.assertEqual([path.rsplit("/", 1)[-1] for path in paths], ["props", "apply-template", "tokenize"])

    def test_three_adapters_use_same_model_and_fulltext_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            passages = [{"passage_id": "p1", "canonical_text": "liberté constitutionnelle", "text_hash": "h1",
                         "article_number": 1, "paragraph_index": 0, "page_spans": [1]},
                        {"passage_id": "p2", "canonical_text": "droit de vote", "text_hash": "h2",
                         "article_number": 2, "paragraph_index": 0, "page_spans": [2]}]
            pp, mp, sp = root / "passages.jsonl", root / "manifest.json", root / "systems.json"
            write_jsonl(pp, passages)
            mp.write_text(json.dumps({"passages_hash": digest(pp.read_bytes()), "source_url": "https://example.org/pdf"}))
            sp.write_text(json.dumps({
                "fulltext": {"model": "Qwen", "prompt_sha256": prompt_hash(), "context_mode": "fulltext"},
                "bm25_rag": {"model": "Qwen", "prompt_sha256": prompt_hash(), "strategy": "bm25"},
                "selected_pipeline": {"model": "Qwen", "prompt_sha256": prompt_hash(), "strategy": "bm25", "top_k": 1},
            }))
            made = []
            class FakeGenerator:
                def __init__(self, **kwargs):
                    made.append(kwargs)
                def generate(self, question, supplied, manifest):
                    return {"status": "insufficient_evidence", "claims": [], "sources": [], "limitations": ""}
            runners = build_runners(pp, mp, sp, generator_factory=FakeGenerator)
            self.assertEqual(set(runners), {"fulltext", "bm25_rag", "selected_pipeline"})
            self.assertEqual(runners["fulltext"]("liberté")["context_passage_ids"], ["p1", "p2"])
            self.assertEqual(runners["bm25_rag"]("liberté")["context_passage_ids"], ["p1"])
            self.assertEqual(runners["selected_pipeline"]("liberté")["context_passage_ids"], ["p1"])
            self.assertTrue(made[0]["require_token_preflight"])
            self.assertEqual({item["model"] for item in made}, {"Qwen"})


if __name__ == "__main__":
    unittest.main()
