"""Optional local FastAPI service; install with the api extra."""
import json
import logging
import time
import uuid
from urllib.request import urlopen
from functools import lru_cache
from urllib.parse import unquote
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal
from . import __version__
from .evidence import extractive_answer, pack, pack_with_article_leads
from .dialogue import resolve, next_articles
from .retrieval import BM25, Dense, Hybrid, dense_index_dir
from .store import ROOT, corpus_paths, read_jsonl, digest

app = FastAPI(title="Constitution Evidence", version=__version__)
logger = logging.getLogger(__name__)

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "app/index.html")

class DialogueTurn(BaseModel):
    article_numbers: list[Annotated[int, Field(ge=1, le=180)]] = Field(max_length=5)

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    generator: Literal["extractive", "local", "groq"] = "extractive"
    strategy: Literal["bm25", "dense", "hybrid", "hybrid-rerank"] = "bm25"
    expand_references: bool = False
    decompose: bool = False
    history: list[DialogueTurn] = Field(default_factory=list, max_length=3)

class AskResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: Literal["answered", "partially_answered", "needs_clarification", "insufficient_evidence", "out_of_scope"]
    claims: list[dict]
    sources: list[dict]
    limitations: str
    request_id: str
    retrieval_strategy: str
    dialogue: dict
    retrieved_passages: list[dict] = Field(default_factory=list)
    retrieved_passage_count: int = 0
    review_status: str | None = None

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


@lru_cache(maxsize=2)
def _load_articles(manifest_hash: str):
    _, manifest, _ = _load_corpus(manifest_hash)
    article_path, _, _ = corpus_paths()
    if digest(article_path.read_bytes()) != manifest["corpus_hash"]:
        raise ValueError("Articles hash does not match the active manifest")
    rows = read_jsonl(article_path)
    return manifest, {row["article_number"]: row for row in rows}

def corpus():
    _, _, manifest_path = corpus_paths()
    return _load_corpus(digest(manifest_path.read_bytes()))

@lru_cache(maxsize=8)
def _engine(manifest_hash: str, strategy: str):
    bm25, _, passages = _load_corpus(manifest_hash)
    if strategy == "bm25":
        return bm25
    rows = list(passages.values())
    index_dir = dense_index_dir(ROOT / "data/processed/dense-index")
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
        return {"app_version": __version__, "corpus_hash": manifest["corpus_hash"],
                "edition_id": manifest["edition_id"], "review_status": manifest.get("review_status")}
    except (FileNotFoundError, ValueError):
        return {"app_version": __version__, "corpus_hash": None, "review_status": None}


def _retrieved_passages(hits: list[dict], context: list[dict], source_url: str) -> list[dict]:
    supplied = {passage["passage_id"] for passage in context}
    rows = []
    for rank, hit in enumerate(hits, 1):
        preview = " ".join(hit["canonical_text"].split())
        rows.append({"rank": rank, "passage_id": hit["passage_id"],
                     "article_number": hit["article_number"], "page_spans": hit.get("page_spans", []),
                     "source_url": source_url, "retriever": hit.get("retriever"),
                     "included_in_context": hit["passage_id"] in supplied,
                     "preview": preview[:240] + ("…" if len(preview) > 240 else "")})
    return rows

@app.get("/capabilities")
def capabilities():
    """Expose whether the separate loopback model server is reachable."""
    from .local_generation import LocalGenerator
    try:
        generator = LocalGenerator()
        with urlopen(generator.base_url + "/health", timeout=1) as response:
            local_available = response.status == 200
    except (OSError, ValueError):
        local_available = False
    return {"local_generation_available": local_available}


@app.get("/articles")
def articles():
    try:
        _, _, manifest_path = corpus_paths()
        manifest, records = _load_articles(digest(manifest_path.read_bytes()))
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(503, "corpus_unavailable") from exc
    return {"edition_id": manifest["edition_id"], "review_status": manifest.get("review_status"),
            "articles": [{"article_number": number, "page_spans": record["page_spans"]}
                         for number, record in sorted(records.items())]}


@app.get("/articles/{number}")
def article(number: int):
    if not 0 <= number <= 180:
        raise HTTPException(404, "Unknown article")
    try:
        _, _, manifest_path = corpus_paths()
        manifest, records = _load_articles(digest(manifest_path.read_bytes()))
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(503, "corpus_unavailable") from exc
    record = records.get(number)
    if record is None:
        raise HTTPException(404, "Unknown article")
    return {**record, "source_url": manifest["source_url"], "edition_id": manifest["edition_id"],
            "review_status": manifest.get("review_status")}

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    started = time.perf_counter()
    request_id = uuid.uuid4().hex
    dialogue = resolve(request.question, [turn.model_dump() for turn in request.history])
    if dialogue["needs_clarification"]:
        logger.info(json.dumps({"event": "ask_completed", "request_id": request_id,
                                "strategy": request.strategy, "generator": request.generator,
                                "retrieval_calls": 0, "source_count": 0,
                                "status": "needs_clarification", "provider_attempts": 0,
                                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}))
        return {"status": "needs_clarification", "claims": [], "sources": [],
                "clarification_question": "De quel article parlez-vous ?",
                "limitations": "Précisez le numéro de l'article pour continuer.",
                "dialogue": {**dialogue, "next_article_numbers": []},
                "request_id": request_id, "retrieval_strategy": request.strategy,
                "reference_expansion": request.expand_references, "decomposition": None,
                "retrieved_passages": [], "retrieved_passage_count": 0, "review_status": None}
    query = dialogue["resolved_question"]
    try:
        _, _, manifest_path = corpus_paths()
        manifest_hash = digest(manifest_path.read_bytes())
        _, manifest, passage_map = _load_corpus(manifest_hash)
        engine = (_reference_engine(manifest_hash, request.strategy) if request.expand_references
                  else _engine(manifest_hash, request.strategy))
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        if request.strategy == "bm25":
            raise
        logger.warning("retrieval_backend_unavailable: %s", type(exc).__name__)
        raise HTTPException(503, "retrieval_backend_unavailable") from exc
    if request.decompose:
        from .decomposition import retrieve_multi
        from .generation import GenerationError
        try:
            if request.generator == "groq":
                from .groq_generation import GroqDecomposer
                planner = GroqDecomposer()
            else:
                planner = None
            hits, decomposition = retrieve_multi(query, engine, request.top_k, planner=planner)
        except GenerationError as exc:
            raise HTTPException(429 if str(exc) in {"local_provider_busy", "groq_rate_limited"} else 503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            if request.strategy == "bm25":
                raise
            logger.warning("retrieval_backend_unavailable: %s", type(exc).__name__)
            raise HTTPException(503, "retrieval_backend_unavailable") from exc
    else:
        try:
            hits, decomposition = engine.search(query, request.top_k), None
        except Exception as exc:
            if request.strategy == "bm25":
                raise
            logger.warning("retrieval_backend_unavailable: %s", type(exc).__name__)
            raise HTTPException(503, "retrieval_backend_unavailable") from exc
    if request.generator in {"local", "groq"} and hits:
        from .generation import GenerationError
        context = pack_with_article_leads(hits, list(passage_map.values()), 7000)
        if not context:
            raise HTTPException(422, "No retrieved passage fits the model context budget")
        try:
            if request.generator == "local":
                from .local_generation import LocalGenerator
                answer = LocalGenerator().generate(query, context, manifest)
            else:
                from .groq_generation import GroqGenerator
                answer = GroqGenerator().generate(query, context, manifest)
        except GenerationError as exc:
            raise HTTPException(429 if str(exc) in {"local_provider_busy", "groq_rate_limited"} else 503, str(exc)) from exc
    else:
        context = pack(hits, 12000)
        answer = extractive_answer(hits, manifest)
    if decomposition:
        decomposition["context_passage_ids"] = [hit["passage_id"] for hit in context]
    answer["retrieval_strategy"] = request.strategy
    answer["retrieved_passage_count"] = len(hits)
    answer["retrieved_passages"] = _retrieved_passages(hits, context, manifest["source_url"])
    answer["review_status"] = manifest.get("review_status")
    answer["reference_expansion"] = request.expand_references
    answer["decomposition"] = decomposition
    answer["dialogue"] = {**dialogue, "next_article_numbers": next_articles(query, answer["sources"])}
    answer["request_id"] = request_id
    logger.info(json.dumps({"event": "ask_completed", "request_id": request_id,
                            "corpus_hash": manifest.get("corpus_hash"), "strategy": request.strategy,
                            "generator": request.generator, "retrieval_calls": decomposition["retrieval_calls"] if decomposition else 1,
                            "source_count": len(answer["sources"]), "status": answer["status"],
                            "usage": answer.get("usage"), "provider_attempts": answer.get("provider_attempts", 0),
                            "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}, ensure_ascii=False))
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
