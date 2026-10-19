import contextlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from constitution_evidence.generation import GenerationError
from constitution_evidence.store import digest, read_jsonl, write_jsonl
from scripts.kaggle_final_runtime import MODEL_REVISION, ROPE_SCALING, TransformersGenerator, seed_previous_results


class Tensor:
    def __init__(self, tokens):
        self.shape = (1, tokens)

    def to(self, device):
        return self


class Generated:
    def numel(self):
        return 12


class Output:
    def __getitem__(self, key):
        return Generated()


class Tokenizer:
    eos_token_id = 1

    def __init__(self, tokens=100):
        self.tokens = tokens
        self.messages = None

    def apply_chat_template(self, messages, **options):
        self.messages = messages
        assert options["enable_thinking"] is False
        return Tensor(self.tokens)

    def decode(self, generated, **options):
        return json.dumps({"status": "answered", "claims": [{"text": "Le droit à la vie est protégé.",
            "evidence": [{"passage_id": "p1", "quote": "La loi protège ce droit."}]}],
            "limitations": "", "clarification_question": ""})


class Model:
    device = "cpu"

    def __init__(self):
        self.calls = 0
        self.last_kwargs = None

    def generate(self, *args, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return Output()


class KaggleFinalTests(unittest.TestCase):
    def setUp(self):
        self.passage = {"passage_id": "p1", "canonical_text": "La loi protège ce droit.",
                        "text_hash": "h", "article_number": 20, "page_spans": [7]}
        self.manifest = {"source_url": "https://example.org/constitution.pdf", "review_status": "reviewed"}
        self.torch = types.ModuleType("torch")
        self.torch.inference_mode = contextlib.nullcontext

    def test_answer_uses_pinned_model_and_validated_source_quote(self):
        tokenizer, model = Tokenizer(), Model()
        generator = TransformersGenerator(tokenizer, model, model_revision=MODEL_REVISION)
        with patch.dict(sys.modules, {"torch": self.torch}):
            answer = generator.generate("Que dit l'article 20 ?", [self.passage], self.manifest)
        self.assertEqual(answer["status"], "answered")
        self.assertEqual(answer["claims"][0]["evidence_spans"][0]["quote"], "La loi protège ce droit.")
        self.assertEqual(answer["model_revision"], MODEL_REVISION)
        self.assertEqual(model.calls, 1)
        self.assertIn("Schéma JSON requis", tokenizer.messages[1]["content"])
        self.assertNotIn("cache_implementation", model.last_kwargs)

    def test_full_text_uses_offloaded_cache(self):
        model = Model()
        generator = TransformersGenerator(Tokenizer(), model, model_revision=MODEL_REVISION,
                                          require_token_preflight=True)
        with patch.dict(sys.modules, {"torch": self.torch}):
            generator.generate("Que dit l'article 20 ?", [self.passage], self.manifest)
        self.assertEqual(model.last_kwargs["cache_implementation"], "offloaded")

    def test_full_text_budget_fails_before_generation(self):
        model = Model()
        generator = TransformersGenerator(Tokenizer(tokens=65000), model, model_revision=MODEL_REVISION)
        with patch.dict(sys.modules, {"torch": self.torch}):
            with self.assertRaisesRegex(GenerationError, "budget_exceeded"):
                generator.generate("Que dit l'article 20 ?", [self.passage], self.manifest)
        self.assertEqual(model.calls, 0)

    def test_recovery_carries_only_prior_retrieval_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior = root / "runs/previous-final-results"
            prior_run = prior / "runs/final-reserved-qwen4b-transformers"
            current_release = root / "runs/release-candidate/manifest.json"
            prior_release = prior / "runs/release-candidate/manifest.json"
            questions_path = root / "runs/complete-owner-reviewed-benchmark.jsonl"
            write_jsonl(questions_path, [{"question_id": "test-001", "family_id": "f1", "split": "test"}])
            common = {"corpus_hash": "corpus", "corpus_manifest_sha256": "corpus-manifest",
                      "questions_sha256": digest(questions_path.read_bytes()),
                      "selection_sha256": "selection", "systems_sha256": "systems",
                      "analysis_plan_sha256": "plan", "lock_sha256": "lock"}
            for path, commit in ((current_release, "new"), (prior_release, "old")):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({**common, "commit": commit}))
            prior_run.mkdir(parents=True)
            (prior_run / "manifest.json").write_text(json.dumps({
                "question_ids": ["test-001"], "questions_sha256": common["questions_sha256"],
                "release_sha256": digest(prior_release.read_bytes())}))
            (prior_run / "model-provenance.json").write_text(json.dumps({
                "model_id": "Qwen/Qwen3-4B", "model_revision": MODEL_REVISION,
                "quantization": "bitsandbytes-nf4", "rope_scaling": ROPE_SCALING}))
            row = {"question_id": "test-001", "family_id": "f1", "answer": {"status": "answered"},
                   "error": None}
            for system in ("bm25_rag", "selected_pipeline"):
                write_jsonl(prior_run / system / "answers.jsonl", [row])
            (prior / "source-archive-sha256.txt").write_text("archive-hash\n")
            output = root / "runs/final-reserved-qwen4b-transformers"
            lineage = seed_previous_results(root, output)
            self.assertEqual(lineage["carried_systems"], {"bm25_rag": 1, "selected_pipeline": 1})
            self.assertFalse((output / "fulltext/answers.jsonl").exists())
            self.assertEqual(read_jsonl(output / "bm25_rag/answers.jsonl"), [row])
            self.assertEqual(seed_previous_results(root, output), lineage)


if __name__ == "__main__":
    unittest.main()
