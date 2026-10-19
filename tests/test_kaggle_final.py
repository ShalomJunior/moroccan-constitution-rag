import contextlib
import json
import sys
import types
import unittest
from unittest.mock import patch

from constitution_evidence.generation import GenerationError
from scripts.kaggle_final_runtime import MODEL_REVISION, TransformersGenerator


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

    def generate(self, *args, **kwargs):
        self.calls += 1
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

    def test_full_text_budget_fails_before_generation(self):
        model = Model()
        generator = TransformersGenerator(Tokenizer(tokens=65000), model, model_revision=MODEL_REVISION)
        with patch.dict(sys.modules, {"torch": self.torch}):
            with self.assertRaisesRegex(GenerationError, "budget_exceeded"):
                generator.generate("Que dit l'article 20 ?", [self.passage], self.manifest)
        self.assertEqual(model.calls, 0)


if __name__ == "__main__":
    unittest.main()
