"""Fixed Qwen adapters for the three-system reserved evaluation."""
import json
from pathlib import Path

from .decomposition import LocalDecomposer, retrieve_multi
from .evidence import extractive_answer, pack
from .local_generation import LOCAL_PROMPT_VERSION, LocalGenerator
from .references import ReferenceExpander
from .retrieval import BM25, Dense, Hybrid
from .release import FINAL_SYSTEMS
from .store import digest, read_jsonl


def prompt_hash() -> str:
    from .generation import INSTRUCTIONS
    from .local_generation import RAW_SCHEMA
    return digest(json.dumps({"instructions": INSTRUCTIONS, "schema": RAW_SCHEMA,
                              "version": LOCAL_PROMPT_VERSION}, ensure_ascii=False, sort_keys=True))


def build_runners(passages_path: Path, manifest_path: Path, systems_path: Path,
                  articles_path: Path | None = None, generator_factory=LocalGenerator) -> dict:
    """Build identical-model generation runners from a frozen system specification."""
    manifest = json.loads(manifest_path.read_text())
    if digest(passages_path.read_bytes()) != manifest["passages_hash"]:
        raise ValueError("Passages differ from the corpus manifest")
    passages = read_jsonl(passages_path)
    systems = json.loads(systems_path.read_text())
    if set(systems) != set(FINAL_SYSTEMS):
        raise ValueError("Exactly three final system specifications are required")
    models = {systems[name].get("model") for name in FINAL_SYSTEMS}
    hashes = {systems[name].get("prompt_sha256") for name in FINAL_SYSTEMS}
    if len(models) != 1 or None in models or len(hashes) != 1 or hashes != {prompt_hash()}:
        raise ValueError("All systems must use one model and the current Qwen prompt")
    if systems["fulltext"].get("context_mode") != "fulltext" or systems["bm25_rag"].get("strategy") != "bm25":
        raise ValueError("Full-text and BM25 baselines are required")
    selected = systems["selected_pipeline"]
    strategy = selected.get("strategy")
    if strategy not in {"bm25", "dense", "hybrid", "hybrid-rerank"}:
        raise ValueError("Selected retrieval strategy is invalid")
    top_k = selected.get("top_k", 5)
    context_chars = selected.get("max_context_chars", 7000)
    if not isinstance(top_k, int) or not 1 <= top_k <= 20 or not isinstance(context_chars, int) or context_chars <= 0:
        raise ValueError("Selected retrieval limits are invalid")
    if selected.get("expand_references") and articles_path is None:
        raise ValueError("Reference expansion needs the articles file")
    if selected.get("expand_references") and digest(articles_path.read_bytes()) != manifest["corpus_hash"]:
        raise ValueError("Articles differ from the corpus manifest")
    model = models.pop()
    fulltext_chars = sum(len(p["canonical_text"]) + len(p["passage_id"]) + 5 for p in passages) + 1
    fulltext_generator = generator_factory(model=model, max_context_chars=fulltext_chars,
                                           require_token_preflight=True)
    retrieval_generator = generator_factory(model=model, max_context_chars=max(8000, context_chars + 2000))
    bm25 = BM25(passages)
    if strategy == "bm25":
        selected_engine = bm25
    elif strategy == "dense":
        selected_engine = Dense(passages)
    else:
        selected_engine = Hybrid(passages, rerank=strategy == "hybrid-rerank")
    if selected.get("expand_references"):
        selected_engine = ReferenceExpander(selected_engine, read_jsonl(articles_path), passages,
                                            review_status=manifest.get("review_status", "unreviewed_ocr"))

    def answer(question, supplied, generator):
        result = generator.generate(question, supplied, manifest) if supplied else extractive_answer([], manifest)
        return {"answer": result, "context_passage_ids": [p["passage_id"] for p in supplied]}

    def fulltext(question):
        return answer(question, passages, fulltext_generator)

    def bm25_rag(question):
        return answer(question, pack(bm25.search(question, 5), 7000), retrieval_generator)

    def selected_pipeline(question):
        if selected.get("decompose"):
            planner = LocalDecomposer(model=model)
            hits, _ = retrieve_multi(question, selected_engine, top_k, planner=planner)
        else:
            hits = selected_engine.search(question, top_k)
        return answer(question, pack(hits, context_chars), retrieval_generator)

    return {"fulltext": fulltext, "bm25_rag": bm25_rag, "selected_pipeline": selected_pipeline}
