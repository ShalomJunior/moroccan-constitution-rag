import contextlib
import hashlib
import importlib
import json
import os
import runpy
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from constitution_evidence.generation import GenerationError
from constitution_evidence.store import digest, read_jsonl, write_jsonl
from scripts.kaggle_final_runtime import (
    MODEL_REVISION, PREFILL_CHUNK_TOKENS, ROPE_SCALING, TransformersGenerator,
    choose_gpu_placement, execute, load_model, require_dual_gpu, seed_previous_results,
)


class Tensor:
    def __init__(self, tokens):
        self.shape = (1, tokens)

    def to(self, device):
        return self

    def __getitem__(self, key):
        if isinstance(key, tuple) and isinstance(key[1], slice):
            start, stop, step = key[1].indices(self.shape[-1])
            return Tensor(len(range(start, stop, step)))
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
    config = object()

    def __init__(self):
        self.calls = 0
        self.last_kwargs = None
        self.forward_chunks = []

    def __call__(self, **kwargs):
        self.forward_chunks.append((kwargs["input_ids"].shape[-1], kwargs["attention_mask"].shape[-1]))
        if isinstance(kwargs.get("past_key_values"), dict):
            kwargs["past_key_values"]["length"] = kwargs["past_key_values"].get("length", 0) + kwargs["input_ids"].shape[-1]
        return object()

    def generate(self, *args, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        if isinstance(kwargs.get("past_key_values"), dict):
            self.assert_cache_has_one_unprocessed_token(kwargs)
        return Output()

    @staticmethod
    def assert_cache_has_one_unprocessed_token(kwargs):
        assert kwargs["input_ids"].shape[-1] == kwargs["past_key_values"]["length"] + 1


class KaggleFinalTests(unittest.TestCase):
    def setUp(self):
        self.passage = {"passage_id": "p1", "canonical_text": "La loi protège ce droit.",
                        "text_hash": "h", "article_number": 20, "page_spans": [7]}
        self.manifest = {"source_url": "https://example.org/constitution.pdf", "review_status": "reviewed"}
        self.torch = types.ModuleType("torch")
        self.torch.inference_mode = contextlib.nullcontext
        self.torch.ones_like = lambda tensor: Tensor(tensor.shape[-1])

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
        self.assertEqual(model.last_kwargs["attention_mask"].shape, (1, 100))

    def test_short_full_text_uses_dynamic_cache(self):
        model = Model()
        generator = TransformersGenerator(Tokenizer(), model, model_revision=MODEL_REVISION,
                                          require_token_preflight=True)
        with patch.dict(sys.modules, {"torch": self.torch}):
            generator.generate("Que dit l'article 20 ?", [self.passage], self.manifest)
        self.assertNotIn("cache_implementation", model.last_kwargs)

    def test_full_text_prefills_in_bounded_chunks(self):
        model = Model()
        tokens = PREFILL_CHUNK_TOKENS * 2 + 13
        generator = TransformersGenerator(Tokenizer(tokens=tokens), model, model_revision=MODEL_REVISION,
                                          require_token_preflight=True)
        fake_transformers = types.ModuleType("transformers")
        fake_transformers.DynamicCache = lambda **kwargs: kwargs
        with patch.dict(sys.modules, {"torch": self.torch, "transformers": fake_transformers}):
            generator.generate("Que dit l'article 20 ?", [self.passage], self.manifest)
        self.assertEqual(model.forward_chunks, [(512, 512), (512, 1024), (12, 1036)])
        self.assertEqual(model.last_kwargs["attention_mask"].shape, (1, tokens))
        self.assertEqual(model.last_kwargs["input_ids"].shape, (1, tokens))
        self.assertEqual(model.last_kwargs["past_key_values"]["length"], tokens - 1)
        self.assertIn("past_key_values", model.last_kwargs)
        self.assertFalse(model.last_kwargs["past_key_values"]["offloading"])

    def test_two_gpu_memory_check_rejects_single_gpu(self):
        cuda = types.SimpleNamespace(is_available=lambda: True, device_count=lambda: 1)
        with self.assertRaisesRegex(RuntimeError, "T4 x2"):
            require_dual_gpu(types.SimpleNamespace(cuda=cuda))

    def test_two_t4s_are_accepted_without_an_arbitrary_free_memory_threshold(self):
        cuda = types.SimpleNamespace(
            is_available=lambda: True, device_count=lambda: 2,
            get_device_properties=lambda index: types.SimpleNamespace(total_memory=15 * 1024**3),
            mem_get_info=lambda index: (_ for _ in ()).throw(AssertionError("free-memory probe")))
        require_dual_gpu(types.SimpleNamespace(cuda=cuda))

    def test_model_load_balances_weights_across_two_gpus(self):
        cuda = types.SimpleNamespace(is_available=lambda: True, device_count=lambda: 2,
                                     get_device_properties=lambda index: types.SimpleNamespace(
                                         total_memory=15 * 1024**3),
                                     mem_get_info=lambda index: (15 * 1024**3, 15 * 1024**3),
                                     get_device_name=lambda index: f"T4-{index}")
        fake_torch = types.ModuleType("torch")
        fake_torch.cuda = cuda
        fake_torch.float16 = "float16"
        fake_torch.__version__ = "test"
        calls = {}
        loaded = Model()
        loaded.hf_device_map = {"model.layers.0": 0, "model.layers.1": 1}
        loaded.eval = lambda: None
        fake_transformers = types.ModuleType("transformers")
        fake_transformers.__version__ = "4.57.6"
        fake_transformers.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *args, **kwargs: Tokenizer())
        fake_transformers.AutoConfig = types.SimpleNamespace(
            from_pretrained=lambda *args, **kwargs: types.SimpleNamespace())
        fake_transformers.BitsAndBytesConfig = lambda **kwargs: kwargs
        def from_pretrained(*args, **kwargs):
            calls.update(kwargs)
            return loaded
        fake_transformers.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=from_pretrained)
        fake_hub = types.ModuleType("huggingface_hub")
        fake_hub.snapshot_download = lambda **kwargs: "/snapshot"
        with patch.dict(sys.modules, {"torch": fake_torch, "transformers": fake_transformers,
                                      "huggingface_hub": fake_hub}):
            _, model, provenance = load_model()
        self.assertIs(model, loaded)
        self.assertEqual(calls["device_map"], "balanced")
        self.assertEqual(calls["max_memory"], {0: "13GiB", 1: "13GiB"})
        self.assertEqual(provenance["gpus"], ["T4-0", "T4-1"])
        cuda.mem_get_info = lambda index: (
            (3 * 1024**3, 15 * 1024**3) if index == 0 else (14 * 1024**3, 15 * 1024**3))
        loaded.hf_device_map = {"": 1}
        with patch.dict(sys.modules, {"torch": fake_torch, "transformers": fake_transformers,
                                      "huggingface_hub": fake_hub}):
            _, model, provenance = load_model()
        self.assertIs(model, loaded)
        self.assertEqual(calls["device_map"], {"": 1})
        self.assertEqual(provenance["placement"]["selected_gpu"], 1)

    def test_placement_avoids_a_t4_occupied_by_another_process(self):
        cuda = types.SimpleNamespace(mem_get_info=lambda index: (
            (3 * 1024**3, 15 * 1024**3) if index == 0 else (14 * 1024**3, 15 * 1024**3)))
        device_map, max_memory, provenance = choose_gpu_placement(types.SimpleNamespace(cuda=cuda))
        self.assertEqual(device_map, {"": 1})
        self.assertEqual(max_memory, {1: "12GiB"})
        self.assertEqual(provenance["strategy"], "less_busy_gpu")
        self.assertEqual(provenance["selected_gpu"], 1)

    def test_notebook_runs_gpu_evaluation_in_a_child_process(self):
        notebook = json.loads((Path(__file__).parents[1] / "notebooks/kaggle_final.ipynb").read_text())
        cell = "".join(notebook["cells"][4]["source"])
        calls = []
        root = Path("/kaggle/working/moroccan-constitution-rag")
        command = types.SimpleNamespace(run=lambda *args, **kwargs: calls.append((args, kwargs)))
        exec(cell, {"subprocess": command, "sys": types.SimpleNamespace(executable="python"),
                    "ROOT": root})
        self.assertEqual(calls, [((["python", "-m", "scripts.kaggle_final_worker", str(root),
                                   "--batch-size", "25"],),
                                  {"check": True, "cwd": root})])

    def test_saved_notebook_installs_without_requiring_a_kernel_restart(self):
        notebook = json.loads((Path(__file__).parents[1] / "notebooks/kaggle_final.ipynb").read_text())
        cell = "".join(notebook["cells"][2]["source"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = []
            command = types.SimpleNamespace(run=lambda *args, **kwargs: calls.append((args, kwargs)))
            exec(cell, {"Path": lambda path: root / "env.txt", "subprocess": command,
                        "sys": types.SimpleNamespace(executable="python"), "ROOT": root,
                        "hashlib": hashlib, "importlib": importlib, "json": json})
            self.assertEqual(len(calls), 1)
            self.assertTrue((root / "env.txt").is_file())

    def test_worker_disables_xla_gpu_claim_before_importing_runtime(self):
        observed = {}
        fake_runtime = types.ModuleType("scripts.kaggle_final_runtime")
        fake_runtime.execute = lambda root: None
        with patch.dict(os.environ, {"JAX_PLATFORMS": "cuda",
                                     "XLA_PYTHON_CLIENT_PREALLOCATE": "true",
                                     "USE_FLAX": "1", "USE_TF": "1"}), patch.dict(
                                         sys.modules, {"scripts.kaggle_final_runtime": fake_runtime}):
            runpy.run_module("scripts.kaggle_final_worker", run_name="test_worker")
            observed.update({key: os.environ[key] for key in (
                "JAX_PLATFORMS", "XLA_PYTHON_CLIENT_PREALLOCATE", "USE_FLAX", "USE_TF")})
        self.assertEqual(observed, {"JAX_PLATFORMS": "cpu",
                                    "XLA_PYTHON_CLIENT_PREALLOCATE": "false",
                                    "USE_FLAX": "0", "USE_TF": "0"})

    def test_resume_accepts_a_new_gpu_placement_for_the_same_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            placements = iter((0, 1))
            def model():
                gpu = next(placements)
                return None, None, {"model_id": "Qwen/Qwen3-4B", "model_revision": MODEL_REVISION,
                                    "quantization": "bitsandbytes-nf4", "placement": {"selected_gpu": gpu},
                                    "device_map": {"": str(gpu)}}
            with patch("scripts.kaggle_final_runtime.verify_bundle", return_value={
                    "release_sha256": "release", "commit": "commit"}), patch(
                    "scripts.kaggle_final_runtime.seed_previous_results"), patch(
                    "scripts.kaggle_final_runtime.load_model", side_effect=model), patch(
                    "scripts.kaggle_final_runtime.build_runners", return_value={}), patch(
                    "scripts.kaggle_final_runtime.run_reserved_test", return_value={
                    "status": "partial"}) as run:
                execute(root, max_new_fulltext=25)
                execute(root, max_new_fulltext=25)
            provenance = json.loads((root / "runs/final-reserved-qwen4b-transformers/model-provenance.json").read_text())
            self.assertEqual(len(provenance["placement_history"]), 2)
            self.assertEqual(run.call_args.kwargs["max_new_fulltext"], 25)

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
            write_jsonl(prior_run / "fulltext/answers.jsonl",
                        [{**row, "answer": None,
                          "error": {"type": "OutOfMemoryError", "message": "CUDA OOM"}}])
            (prior / "source-archive-sha256.txt").write_text("archive-hash\n")
            output = root / "runs/final-reserved-qwen4b-transformers"
            lineage = seed_previous_results(root, output)
            self.assertEqual(lineage["carried_systems"], {"bm25_rag": 1, "selected_pipeline": 1})
            self.assertFalse((output / "fulltext/answers.jsonl").exists())
            self.assertEqual(read_jsonl(output / "bm25_rag/answers.jsonl"), [row])
            self.assertEqual(seed_previous_results(root, output), lineage)
            shutil.rmtree(output)
            write_jsonl(prior_run / "fulltext/answers.jsonl", [row])
            second = seed_previous_results(root, output)
            self.assertEqual(second["carried_systems"]["fulltext"], 1)
            self.assertEqual(read_jsonl(output / "fulltext/answers.jsonl"), [row])


if __name__ == "__main__":
    unittest.main()
