"""Pinned Transformers execution of the frozen three-system evaluation."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from constitution_evidence.campaign import build_runners
from constitution_evidence.generation import GenerationError
from constitution_evidence.local_generation import (
    LOCAL_PROMPT_VERSION, RAW_SCHEMA, answer_messages, checked_answer,
)
from constitution_evidence.release import assert_reserved_test_ready, run_reserved_test

MODEL_ID = "Qwen/Qwen3-4B"
MODEL_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"
MODEL_ALIAS = "Qwen3-4B"
TOKEN_LIMIT = 32768
MAX_NEW_TOKENS = 768
TOKEN_RESERVE = 128
RUN_ID = "final-reserved-qwen4b-transformers"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_bundle(root: Path) -> dict:
    marker = json.loads((root / "runs/kaggle-bundle.json").read_text())
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if commit != marker["commit"]:
        raise ValueError("Bundle Git revision differs from its manifest")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip():
        raise ValueError("Bundle checkout is dirty")
    for name, expected in marker["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or sha256(root / relative) != expected:
            raise ValueError(f"Bundle input differs: {name}")
    release = root / "runs/release-candidate/manifest.json"
    if sha256(release) != marker["release_sha256"]:
        raise ValueError("Bundle release manifest differs")
    questions = root / "runs/complete-owner-reviewed-benchmark.jsonl"
    assert_reserved_test_ready(release, questions, root / "data/processed/manifest.json")
    return marker


class TransformersGenerator:
    def __init__(self, tokenizer, model, *, model_revision: str, max_context_chars: int = 8000,
                 require_token_preflight: bool = False):
        self.tokenizer = tokenizer
        self.backend = model
        self.model_revision = model_revision
        self.model = MODEL_ALIAS
        self.max_context_chars = max_context_chars
        self.require_token_preflight = require_token_preflight

    def generate(self, question: str, supplied: list[dict], manifest: dict) -> dict:
        import torch

        messages = answer_messages(question, supplied, self.max_context_chars)
        messages[1]["content"] += "\n\nSchéma JSON requis :\n" + json.dumps(
            RAW_SCHEMA, ensure_ascii=False, sort_keys=True)
        input_ids = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            enable_thinking=False, return_tensors="pt")
        prompt_tokens = int(input_ids.shape[-1])
        required = prompt_tokens + MAX_NEW_TOKENS + TOKEN_RESERVE
        if required > TOKEN_LIMIT:
            raise GenerationError(f"budget_exceeded: need {required} tokens; native context={TOKEN_LIMIT}")
        with torch.inference_mode():
            output = self.backend.generate(
                input_ids.to(self.backend.device), max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False, pad_token_id=self.tokenizer.eos_token_id, use_cache=True)
        generated = output[0, prompt_tokens:]
        content = self.tokenizer.decode(generated, skip_special_tokens=True)
        try:
            raw = json.loads(content)
        except (ValueError, TypeError) as exc:
            raise GenerationError(f"invalid_output: model did not return JSON: {exc}") from exc
        result = checked_answer(
            raw, supplied, manifest, self.model, LOCAL_PROMPT_VERSION,
            {"prompt_tokens": prompt_tokens, "completion_tokens": int(generated.numel()),
             "model_id": MODEL_ID, "model_revision": self.model_revision,
             "quantization": "bitsandbytes-nf4"})
        result["model_id"] = MODEL_ID
        result["model_revision"] = self.model_revision
        return result


def load_model():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("Select a Kaggle GPU accelerator")
    snapshot = snapshot_download(
        repo_id=MODEL_ID, revision=MODEL_REVISION,
        allow_patterns=["*.json", "*.jinja", "*.model", "*.txt", "*.safetensors"])
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    quantization = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, local_files_only=True, quantization_config=quantization,
        device_map="auto", dtype=torch.float16)
    model.eval()
    provenance = {"model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                  "quantization": "bitsandbytes-nf4", "native_context_tokens": TOKEN_LIMIT,
                  "transformers_version": transformers.__version__, "torch_version": torch.__version__,
                  "gpu": torch.cuda.get_device_name(0)}
    return tokenizer, model, provenance


def execute(root: Path) -> dict:
    marker = verify_bundle(root)
    tokenizer, model, provenance = load_model()
    output = root / "runs" / RUN_ID
    output.mkdir(parents=True, exist_ok=True)
    provenance.update({"release_sha256": marker["release_sha256"], "commit": marker["commit"]})
    provenance_path = output / "model-provenance.json"
    if provenance_path.exists() and json.loads(provenance_path.read_text()) != provenance:
        raise ValueError("This run ID belongs to a different model or environment")
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n")

    def generator_factory(**kwargs):
        if kwargs.get("model") != MODEL_ALIAS:
            raise ValueError("Frozen model differs from the pinned Transformers model")
        return TransformersGenerator(
            tokenizer, model, model_revision=MODEL_REVISION,
            max_context_chars=kwargs.get("max_context_chars", 8000),
            require_token_preflight=kwargs.get("require_token_preflight", False))

    runners = build_runners(
        root / "data/processed/passages.jsonl", root / "data/processed/manifest.json",
        root / "configs/final_systems.json", root / "data/processed/articles.jsonl",
        generator_factory=generator_factory)
    return run_reserved_test(
        root / "runs/release-candidate/manifest.json",
        root / "runs/complete-owner-reviewed-benchmark.jsonl",
        root / "data/processed/manifest.json", output, runners)


def export_results(root: Path, destination: Path) -> dict:
    verify_bundle(root)
    output = root / "runs" / RUN_ID
    files = [output / "manifest.json", output / "model-provenance.json"]
    systems = ("fulltext", "bm25_rag", "selected_pipeline")
    files.extend(path for system in systems if (path := output / system / "answers.jsonl").is_file())
    files.append(root / "runs/release-candidate/manifest.json")
    if any(not path.is_file() for path in files) or len(files) <= 3:
        raise FileNotFoundError("No saved answers yet; start the evaluation first")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
    return {"archive": str(destination), "sha256": sha256(destination),
            "answer_rows": {name: sum(1 for _ in (output / name / "answers.jsonl").open())
                            if (output / name / "answers.jsonl").is_file() else 0
                            for name in systems}}
