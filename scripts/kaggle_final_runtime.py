"""Pinned Transformers execution of the frozen three-system evaluation."""
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

from constitution_evidence.campaign import build_runners
from constitution_evidence.generation import GenerationError
from constitution_evidence.local_generation import (
    LOCAL_PROMPT_VERSION, RAW_SCHEMA, answer_messages, checked_answer,
)
from constitution_evidence.release import assert_reserved_test_ready, run_reserved_test
from constitution_evidence.store import digest, read_jsonl, write_jsonl

MODEL_ID = "Qwen/Qwen3-4B"
MODEL_REVISION = "1cfa9a7208912126459214e8b04321603b3df60c"
MODEL_ALIAS = "Qwen3-4B"
TOKEN_LIMIT = 65536
ROPE_SCALING = {"rope_type": "yarn", "factor": 2.0,
                "original_max_position_embeddings": 32768}
MAX_NEW_TOKENS = 768
TOKEN_RESERVE = 128
PREFILL_CHUNK_TOKENS = 512
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
            raise GenerationError(f"budget_exceeded: need {required} tokens; context capacity={TOKEN_LIMIT}")
        attention_mask = torch.ones_like(input_ids)
        with torch.inference_mode():
            if self.require_token_preflight and prompt_tokens > PREFILL_CHUNK_TOKENS:
                generated = self._generate_chunked(input_ids, attention_mask)
                cache_strategy = "gpu-resident-chunked"
            else:
                output = self.backend.generate(
                    input_ids.to(self.backend.device), attention_mask=attention_mask.to(self.backend.device),
                    max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id, use_cache=True)
                generated = output[0, prompt_tokens:]
                cache_strategy = "dynamic"
        content = self.tokenizer.decode(generated, skip_special_tokens=True)
        try:
            raw = json.loads(content)
        except (ValueError, TypeError) as exc:
            raise GenerationError(f"invalid_output: model did not return JSON: {exc}") from exc
        result = checked_answer(
            raw, supplied, manifest, self.model, LOCAL_PROMPT_VERSION,
            {"prompt_tokens": prompt_tokens, "completion_tokens": int(generated.numel()),
             "model_id": MODEL_ID, "model_revision": self.model_revision,
             "quantization": "bitsandbytes-nf4",
             "cache_implementation": cache_strategy})
        result["model_id"] = MODEL_ID
        result["model_revision"] = self.model_revision
        return result

    def _generate_chunked(self, input_ids, attention_mask):
        """Prefill all but the last token, then let HF generate consume that token."""
        from transformers import DynamicCache

        device = self.backend.device
        input_ids = input_ids.to(device)
        attention_mask = attention_mask.to(device)
        cache = DynamicCache(config=self.backend.config, offloading=False)
        prompt_tokens = int(input_ids.shape[-1])
        for start in range(0, prompt_tokens - 1, PREFILL_CHUNK_TOKENS):
            end = min(start + PREFILL_CHUNK_TOKENS, prompt_tokens - 1)
            self.backend(input_ids=input_ids[:, start:end], attention_mask=attention_mask[:, :end],
                         past_key_values=cache, use_cache=True, logits_to_keep=1)
        output = self.backend.generate(
            input_ids=input_ids, attention_mask=attention_mask,
            past_key_values=cache, max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False, pad_token_id=self.tokenizer.eos_token_id, use_cache=True)
        return output[0, prompt_tokens:]


def load_model():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    require_dual_gpu(torch)
    device_map, max_memory, placement = choose_gpu_placement(torch)
    snapshot = snapshot_download(
        repo_id=MODEL_ID, revision=MODEL_REVISION,
        allow_patterns=["*.json", "*.jinja", "*.model", "*.txt", "*.safetensors"])
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    config = AutoConfig.from_pretrained(snapshot, local_files_only=True)
    config.rope_scaling = ROPE_SCALING
    config.max_position_embeddings = TOKEN_LIMIT
    quantization = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, local_files_only=True, config=config, quantization_config=quantization,
        device_map=device_map, max_memory=max_memory, dtype=torch.float16)
    model.eval()
    placements = {str(device) for device in model.hf_device_map.values()}
    if not placements or not placements <= {"0", "1", "cuda:0", "cuda:1"}:
        raise RuntimeError(f"Qwen must stay on Kaggle GPUs without CPU offloading; map={model.hf_device_map}")
    provenance = {"model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                  "quantization": "bitsandbytes-nf4", "context_capacity_tokens": TOKEN_LIMIT,
                  "fulltext_cache_implementation": "gpu-resident-chunked",
                  "prefill_chunk_tokens": PREFILL_CHUNK_TOKENS,
                  "rope_scaling": ROPE_SCALING,
                  "transformers_version": transformers.__version__, "torch_version": torch.__version__,
                  "gpu": torch.cuda.get_device_name(0),
                  "gpus": [torch.cuda.get_device_name(i) for i in range(2)],
                  "placement": placement,
                  "jax_platforms": os.environ.get("JAX_PLATFORMS"),
                  "xla_preallocate": os.environ.get("XLA_PYTHON_CLIENT_PREALLOCATE"),
                  "device_map": {name: str(device) for name, device in model.hf_device_map.items()}}
    return tokenizer, model, provenance


def require_dual_gpu(torch) -> None:
    if not torch.cuda.is_available() or torch.cuda.device_count() < 2:
        raise RuntimeError("Select the Kaggle T4 x2 accelerator; full-text evaluation needs two GPUs")
    for index in range(2):
        total = torch.cuda.get_device_properties(index).total_memory
        if total < 14 * 1024**3:
            raise RuntimeError(
                f"GPU {index} has only {total / 1024**3:.1f} GiB total memory; "
                "select the Kaggle T4 x2 accelerator")


def choose_gpu_placement(torch) -> tuple[str | dict, dict, dict]:
    """Keep Qwen on available GPUs; avoid a T4 occupied by another process."""
    free = [torch.cuda.mem_get_info(index)[0] for index in range(2)]
    free_gib = [round(value / 1024**3, 2) for value in free]
    if min(free) * 2 < max(free):
        selected = max(range(2), key=free.__getitem__)
        return {"": selected}, {selected: f"{max(1, int(free[selected] / 1024**3) - 2)}GiB"}, {
            "strategy": "less_busy_gpu", "selected_gpu": selected, "free_gib_before_load": free_gib}
    max_memory = {index: f"{max(1, min(13, int(value / 1024**3) - 2))}GiB"
                  for index, value in enumerate(free)}
    return "balanced", max_memory, {"strategy": "balanced", "free_gib_before_load": free_gib}


def seed_previous_results(root: Path, output: Path) -> dict | None:
    """Carry forward unchanged retrieval-system answers from the failed T4 run."""
    previous = root / "runs/previous-final-results"
    if not previous.exists():
        return None
    prior_run = previous / "runs" / RUN_ID
    prior_release = json.loads((previous / "runs/release-candidate/manifest.json").read_text())
    current_release_path = root / "runs/release-candidate/manifest.json"
    current_release = json.loads(current_release_path.read_text())
    immutable = ("corpus_hash", "corpus_manifest_sha256", "questions_sha256",
                 "selection_sha256", "systems_sha256", "analysis_plan_sha256", "lock_sha256")
    if any(prior_release.get(key) != current_release.get(key) for key in immutable):
        raise ValueError("Previous results do not match the frozen corpus, questions, or systems")
    prior_manifest = json.loads((prior_run / "manifest.json").read_text())
    questions = [q for q in read_jsonl(root / "runs/complete-owner-reviewed-benchmark.jsonl")
                 if q["split"] == "test"]
    question_ids = [q["question_id"] for q in questions]
    if (prior_manifest.get("question_ids") != question_ids or
            prior_manifest.get("questions_sha256") != current_release["questions_sha256"] or
            prior_manifest.get("release_sha256") != digest(
                (previous / "runs/release-candidate/manifest.json").read_bytes())):
        raise ValueError("Previous results have a different reserved test inventory")
    prior_model = json.loads((prior_run / "model-provenance.json").read_text())
    if (prior_model.get("model_id") != MODEL_ID or prior_model.get("model_revision") != MODEL_REVISION or
            prior_model.get("quantization") != "bitsandbytes-nf4" or
            prior_model.get("rope_scaling") != ROPE_SCALING):
        raise ValueError("Previous results used a different model configuration")
    copied = {}
    for system in ("bm25_rag", "selected_pipeline"):
        rows = read_jsonl(prior_run / system / "answers.jsonl")
        if [row.get("question_id") for row in rows] != question_ids or any(
                row.get("family_id") != question["family_id"] for row, question in zip(rows, questions)):
            raise ValueError(f"Previous {system} answers are incomplete or out of order")
        copied[system] = rows
    previous_fulltext = prior_run / "fulltext/answers.jsonl"
    if previous_fulltext.exists():
        rows = read_jsonl(previous_fulltext)
        by_id = {row.get("question_id"): row for row in rows}
        families = {q["question_id"]: q["family_id"] for q in questions}
        if (len(by_id) != len(rows) or not set(by_id) <= set(question_ids) or
                any(row.get("family_id") != families[qid] for qid, row in by_id.items())):
            raise ValueError("Previous full-text answers contain unknown or duplicate questions")
        successful = [by_id[qid] for qid in question_ids
                      if qid in by_id and by_id[qid].get("error") is None and by_id[qid].get("answer")]
        if successful:
            copied["fulltext"] = successful
    expected = {"release_sha256": digest(current_release_path.read_bytes()),
                "questions_sha256": current_release["questions_sha256"],
                "question_ids": question_ids,
                "systems": ["fulltext", "bm25_rag", "selected_pipeline"]}
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text()) != expected:
            raise ValueError("Existing run belongs to a different recovery release")
    else:
        if any((output / system / "answers.jsonl").exists() for system in expected["systems"]):
            raise ValueError("Existing answers have no recovery manifest")
        for system, rows in copied.items():
            write_jsonl(output / system / "answers.jsonl", rows)
        manifest_path.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n")
    lineage = {"source_commit": prior_release["commit"],
               "source_archive_sha256": (previous / "source-archive-sha256.txt").read_text().strip(),
               "carried_systems": {system: len(rows) for system, rows in copied.items()},
               "source_fulltext_cache_implementation": prior_model.get("fulltext_cache_implementation"),
               "recovery": "verified previous answers; same model, prompt, corpus and questions"}
    lineage_path = output / "recovery-lineage.json"
    if lineage_path.exists() and json.loads(lineage_path.read_text()) != lineage:
        raise ValueError("Recovery lineage changed")
    lineage_path.write_text(json.dumps(lineage, ensure_ascii=False, indent=2) + "\n")
    return lineage


def execute(root: Path, max_new_fulltext: int | None = None) -> dict:
    marker = verify_bundle(root)
    output = root / "runs" / RUN_ID
    seed_previous_results(root, output)
    tokenizer, model, provenance = load_model()
    output.mkdir(parents=True, exist_ok=True)
    provenance.update({"release_sha256": marker["release_sha256"], "commit": marker["commit"]})
    provenance_path = output / "model-provenance.json"
    current_placement = {"placement": provenance["placement"],
                         "device_map": provenance["device_map"]}
    if provenance_path.exists():
        previous = json.loads(provenance_path.read_text())
        stable_keys = ("model_id", "model_revision", "quantization", "context_capacity_tokens",
                       "fulltext_cache_implementation", "prefill_chunk_tokens", "rope_scaling",
                       "transformers_version", "torch_version", "release_sha256", "commit")
        if any(previous.get(key) != provenance.get(key) for key in stable_keys):
            raise ValueError("This run ID belongs to a different model or environment")
        placements = previous.get("placement_history", [
            {"placement": previous.get("placement"), "device_map": previous.get("device_map")}])
        if current_placement not in placements:
            placements.append(current_placement)
        provenance["placement_history"] = placements
    else:
        provenance["placement_history"] = [current_placement]
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
        root / "data/processed/manifest.json", output, runners,
        fatal_error_types=("OutOfMemoryError", "RuntimeError", "TypeError", "IndexError"),
        max_new_fulltext=max_new_fulltext)


def export_results(root: Path, destination: Path) -> dict:
    verify_bundle(root)
    output = root / "runs" / RUN_ID
    files = [output / "manifest.json", output / "model-provenance.json"]
    if (output / "recovery-lineage.json").is_file():
        files.append(output / "recovery-lineage.json")
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
