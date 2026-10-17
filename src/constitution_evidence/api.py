"""Optional local FastAPI service; install with the api extra."""
import json
from functools import lru_cache
from urllib.parse import unquote
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import __version__
from .evidence import extractive_answer, pack
from .retrieval import BM25
from .store import ROOT, corpus_paths, read_jsonl, digest

app = FastAPI(title="Constitution Evidence", version=__version__)

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "app/index.html")

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    generator: str = Field(default="extractive", pattern="^(extractive|local)$")

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
        engine, manifest, _ = corpus()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
    hits = engine.search(request.question, request.top_k)
    if request.generator == "local":
        from .local_generation import LocalGenerator, GenerationError
        try:
            return LocalGenerator().generate(request.question, pack(hits, 7000), manifest)
        except GenerationError as exc:
            raise HTTPException(503, str(exc)) from exc
    return extractive_answer(hits, manifest)

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
