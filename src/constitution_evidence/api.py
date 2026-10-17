"""Optional local FastAPI service; install with the api extra."""
import json
from functools import lru_cache
from urllib.parse import unquote
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Literal
from . import __version__
from .evidence import extractive_answer, pack
from .retrieval import BM25, Dense, Hybrid
from .store import ROOT, corpus_paths, read_jsonl, digest

app = FastAPI(title="Constitution Evidence", version=__version__)

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "app/index.html")

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    generator: Literal["extractive", "local"] = "extractive"
    strategy: Literal["bm25", "dense", "hybrid", "hybrid-rerank"] = "bm25"
    expand_references: bool = False

@lru_cache(maxsize=2)
def _load_corpus(manifest_hash: str):
    _, passage_path, manifest_path = corpus_paths()
    manifest_bytes = manifest_path.read_bytes()
    if digest(manifest_bytes) != manifest_hash:
        raise ValueError("Manifest changed during corpus load")
    manifest = json.loads(manifest_bytes)
    if digest(passage_path.read_bytes()) != manifest["passages_hash"]:
        raise ValueError("Passages hash does not match the active manifest")
    passages = read_jsonl(passage_path)
    return BM25(passages), manifest, {p["passage_id"]: p for p in passages}

def corpus():
    _, _, manifest_path = corpus_paths()
    return _load_corpus(digest(manifest_path.read_bytes()))

@lru_cache(maxsize=8)
def _engine(manifest_hash: str, strategy: str):
    bm25, _, passages = _load_corpus(manifest_hash)
    if strategy == "bm25":
        return bm25
    rows = list(passages.values())
    index_dir = ROOT / "data/processed/dense-index"
    if strategy == "dense":
        return Dense(rows, index_dir=index_dir)
    return Hybrid(rows, index_dir=index_dir, rerank=strategy == "hybrid-rerank")

@lru_cache(maxsize=8)
def _reference_engine(manifest_hash: str, strategy: str):
    from .references import ReferenceExpander
    article_path, _, _ = corpus_paths()
    _, manifest, passages = _load_corpus(manifest_hash)
    if digest(article_path.read_bytes()) != manifest["corpus_hash"]:
        raise ValueError("Articles hash does not match the active manifest")
    return ReferenceExpander(_engine(manifest_hash, strategy), read_jsonl(article_path),
                             list(passages.values()), review_status=manifest["review_status"])

@app.get("/health")
def health():
    try:
        corpus()
        return {"status": "ok", "corpus": "loaded"}
    except (FileNotFoundError, ValueError):
        return {"status": "degraded", "corpus": "missing"}

@app.get("/version")
def version():
    try:
        _, manifest, _ = corpus()
        return {"app_version": __version__, "corpus_hash": manifest["corpus_hash"], "edition_id": manifest["edition_id"]}
    except (FileNotFoundError, ValueError):
        return {"app_version": __version__, "corpus_hash": None}

@app.post("/ask")
def ask(request: AskRequest):
    try:
        _, _, manifest_path = corpus_paths()
        manifest_hash = digest(manifest_path.read_bytes())
        _, manifest, _ = _load_corpus(manifest_hash)
        engine = (_reference_engine(manifest_hash, request.strategy) if request.expand_references
                  else _engine(manifest_hash, request.strategy))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(503, str(exc)) from exc
    hits = engine.search(request.question, request.top_k)
    if request.generator == "local":
        from .local_generation import LocalGenerator, GenerationError
        try:
            answer = LocalGenerator().generate(request.question, pack(hits, 7000), manifest)
        except GenerationError as exc:
            raise HTTPException(503, str(exc)) from exc
    else:
        answer = extractive_answer(hits, manifest)
    answer["retrieval_strategy"] = request.strategy
    answer["reference_expansion"] = request.expand_references
    return answer

@app.get("/sources/{source_id:path}")
def source(source_id: str):
    try:
        _, manifest, passages = corpus()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
    passage = passages.get(unquote(source_id))
    if not passage:
        raise HTTPException(404, "Unknown passage")
    return {**passage, "source_url": manifest["source_url"], "edition_id": manifest["edition_id"],
            "review_status": manifest["review_status"]}
