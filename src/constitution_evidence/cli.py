import argparse
import json
import re
from pathlib import Path
from . import __version__
from .evidence import extractive_answer, pack
from .evaluation import evaluate, report
from .ingestion import ingest, validate_articles, validate_passages
from .retrieval import BM25, Dense, Hybrid
from .store import ROOT, corpus_paths, read_jsonl, digest

def main(argv=None):
    parser = argparse.ArgumentParser(prog="constitution-evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("--config", type=Path, default=ROOT / "configs/corpus.json")
    p.add_argument("--tessdata", type=Path)
    sub.add_parser("validate-corpus")
    p = sub.add_parser("ask")
    p.add_argument("question")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--strategy", choices=["bm25", "dense", "hybrid", "hybrid-rerank"], default="bm25")
    p.add_argument("--generator", choices=["extractive", "local", "gemini"], default="extractive")
    p.add_argument("--context", choices=["retrieved", "fulltext"], default="retrieved")
    p = sub.add_parser("evaluate")
    p.add_argument("--split", choices=["dev", "validation", "test"], default="dev")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p.add_argument("--run-id", required=True)
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--context-chars", type=int, default=7000)
    p.add_argument("--strategy", choices=["bm25", "dense", "hybrid", "hybrid-rerank"], default="bm25")
    p = sub.add_parser("report")
    p.add_argument("--run-id", required=True)
    sub.add_parser("serve")
    args = parser.parse_args(argv)
    articles, passages, manifest = corpus_paths()
    if args.command == "ingest":
        result = ingest(args.config, tessdata=args.tessdata)
    elif args.command == "validate-corpus":
        records = read_jsonl(articles)
        validate_articles(records)
        chunks = read_jsonl(passages)
        validate_passages(records, chunks)
        metadata = json.loads(manifest.read_text())
        if digest(articles.read_bytes()) != metadata["corpus_hash"]:
            raise ValueError("Corpus hash mismatch")
        if digest(passages.read_bytes()) != metadata["passages_hash"]:
            raise ValueError("Passages hash mismatch")
        result = {"articles": len(records), "passages": len(chunks), "valid": True,
                  "review_status": metadata["review_status"]}
    elif args.command == "ask":
        records = read_jsonl(passages)
        metadata = json.loads(manifest.read_text())
        if digest(passages.read_bytes()) != metadata["passages_hash"]:
            raise ValueError("Passages hash does not match the active manifest")
        if args.strategy == "bm25":
            engine = BM25(records)
        elif args.strategy == "dense":
            engine = Dense(records, index_dir=ROOT / "data/processed/dense-index")
        else:
            engine = Hybrid(records, index_dir=ROOT / "data/processed/dense-index", rerank=args.strategy == "hybrid-rerank")
        hits = engine.search(args.question, args.top_k)
        if args.generator == "extractive":
            if args.context == "fulltext":
                raise ValueError("Fulltext is a generative baseline only")
            result = extractive_answer(hits, metadata)
        elif args.generator == "local":
            if args.context == "fulltext":
                raise ValueError("The local model's context is too small for the fulltext baseline")
            from .local_generation import LocalGenerator
            result = LocalGenerator().generate(args.question, pack(hits, 7000), metadata)
        else:
            from .generation import GeminiGenerator
            supplied = records if args.context == "fulltext" else hits
            result = GeminiGenerator().generate(args.question, supplied, metadata)
    elif args.command == "evaluate":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Run ID must be a simple name of at most 80 characters")
        result = evaluate(args.questions, passages, args.split, ROOT / "runs" / args.run_id,
                          args.k, args.strategy, args.context_chars)
    elif args.command == "report":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Run ID must be a simple name of at most 80 characters")
        result = report(ROOT / "runs" / args.run_id)
    else:
        try:
            import uvicorn
        except ImportError as exc:
            raise SystemExit("Install the API extras: uv pip install -e '.[api]'") from exc
        uvicorn.run("constitution_evidence.api:app", host="127.0.0.1", port=8000)
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
