import argparse
import json
import re
from pathlib import Path
from . import __version__
from .evidence import extractive_answer, pack, pack_with_article_leads
from .evaluation import evaluate, report
from .ingestion import ingest, validate_articles, validate_passages
from .retrieval import BM25, Dense, Hybrid, dense_index_dir
from .store import ROOT, corpus_paths, read_jsonl, digest

def main(argv=None):
    try:
        return _main(argv)
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(f"error: {exc}") from exc


def _main(argv=None):
    parser = argparse.ArgumentParser(prog="constitution-evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("--config", type=Path, default=ROOT / "configs/corpus.json")
    p.add_argument("--tessdata", type=Path)
    p.add_argument("--corrections", type=Path)
    sub.add_parser("validate-corpus")
    p = sub.add_parser("audit-corpus")
    p.add_argument("--output", type=Path, default=ROOT / "reports/ocr-audit.html")
    p = sub.add_parser("ocr-risk-audit")
    p.add_argument("--output", type=Path, default=ROOT / "reports/ocr-risk-audit.md")
    p = sub.add_parser("review-template")
    p.add_argument("--output", type=Path, default=ROOT / "data/annotations/corpus-review.jsonl")
    p = sub.add_parser("certify-corpus")
    p.add_argument("--review", type=Path, default=ROOT / "data/annotations/corpus-review.jsonl")
    p = sub.add_parser("ask")
    p.add_argument("question")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--strategy", choices=["bm25", "dense", "hybrid", "hybrid-rerank"], default="bm25")
    p.add_argument("--expand-references", action="store_true")
    p.add_argument("--decompose", action="store_true", help="Up to three searches; conceptual questions use the selected model backend")
    p.add_argument("--generator", choices=["extractive", "local", "groq", "gemini"], default="extractive")
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
    p = sub.add_parser("compare-runs")
    p.add_argument("left")
    p.add_argument("right")
    p = sub.add_parser("select-validation")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p.add_argument("--policy", type=Path, default=ROOT / "configs/selection_policy.json")
    p.add_argument("run_ids", nargs="+")
    p = sub.add_parser("oracle-run")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p.add_argument("--split", choices=["dev", "validation"], default="dev")
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("bench-retrieval")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/calibration.jsonl")
    p.add_argument("--strategy", choices=["bm25", "dense", "hybrid", "hybrid-rerank"], default="bm25")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("bench-generation")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/calibration.jsonl")
    p.add_argument("--selection", type=Path, default=ROOT / "configs/latency_questions.json")
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("calibrate-groq")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/calibration.jsonl")
    p.add_argument("--run-id", required=True)
    p.add_argument("--max-new", type=int, default=15)
    p.add_argument("--pause-seconds", type=float, default=18.0)
    p = sub.add_parser("release-readiness")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p.add_argument("--selection", type=Path, default=ROOT / "runs/validation-selection.json")
    p.add_argument("--systems", type=Path, default=ROOT / "configs/final_systems.json")
    p.add_argument("--output", type=Path, default=ROOT / "runs/release-candidate/manifest.json")
    p = sub.add_parser("audit-questions")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p = sub.add_parser("test-preflight")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p.add_argument("--release-manifest", type=Path, default=ROOT / "runs/release-candidate/manifest.json")
    p = sub.add_parser("run-reserved-test")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p.add_argument("--release-manifest", type=Path, default=ROOT / "runs/release-candidate/manifest.json")
    p.add_argument("--systems", type=Path, default=ROOT / "configs/final_systems.json")
    p.add_argument("--run-id", required=True)
    p = sub.add_parser("blind-packets")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/questions.jsonl")
    p.add_argument("--release-manifest", type=Path, default=ROOT / "runs/release-candidate/manifest.json")
    p.add_argument("--fulltext", type=Path, required=True)
    p.add_argument("--bm25-rag", type=Path, required=True)
    p.add_argument("--selected-pipeline", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("score-judgments")
    p.add_argument("--mapping", type=Path, required=True)
    p.add_argument("--judgments", type=Path, required=True)
    p.add_argument("--replications", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20261018)
    p = sub.add_parser("reproduce-retrieval")
    p.add_argument("--questions", type=Path, default=ROOT / "data/annotations/robustness_calibration.jsonl")
    p.add_argument("run_ids", nargs="+")
    sub.add_parser("publication-audit")
    sub.add_parser("serve")
    args = parser.parse_args(argv)
    articles, passages, manifest = corpus_paths()
    if args.command == "ingest":
        result = ingest(args.config, tessdata=args.tessdata, corrections=args.corrections)
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
    elif args.command == "audit-corpus":
        from .corrections import write_audit_html
        records = read_jsonl(articles)
        metadata = json.loads(manifest.read_text())
        if digest(articles.read_bytes()) != metadata["corpus_hash"]:
            raise ValueError("Corpus hash mismatch")
        config = json.loads((ROOT / "configs/corpus.json").read_text())
        result = write_audit_html(records, metadata, args.output, ROOT / config["pdf_path"],
                                  ROOT / "data/processed/pages" / metadata["page_cache_key"])
    elif args.command == "ocr-risk-audit":
        from .ocr_quality import write_risk_audit
        result = write_risk_audit(articles, passages, manifest, args.output)
    elif args.command == "review-template":
        from .review import create_review_template
        result = create_review_template(articles, manifest, args.output)
    elif args.command == "certify-corpus":
        from .review import certify_corpus
        result = certify_corpus(articles, manifest, args.review)
    elif args.command == "ask":
        if not args.question.strip() or len(args.question) > 2000 or not 1 <= args.top_k <= 20:
            raise ValueError("Question must be 1–2000 characters and top-k must be 1–20")
        if args.decompose and args.context == "fulltext":
            raise ValueError("Decomposition applies only to retrieved context")
        if args.context == "fulltext" and args.generator == "groq":
            raise ValueError("Groq accepts retrieved context only")
        records = read_jsonl(passages)
        metadata = json.loads(manifest.read_text())
        if digest(passages.read_bytes()) != metadata["passages_hash"]:
            raise ValueError("Passages hash does not match the active manifest")
        if args.context == "fulltext" and args.generator == "local":
            from .local_generation import LocalGenerator
            size = sum(len(row["canonical_text"]) + len(row["passage_id"]) + 5 for row in records) + 1
            result = LocalGenerator(max_context_chars=size, require_token_preflight=True).generate(args.question, records, metadata)
            result["decomposition"] = None
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if args.strategy == "bm25":
            engine = BM25(records)
        elif args.strategy == "dense":
            engine = Dense(records, index_dir=dense_index_dir(ROOT / "data/processed/dense-index"))
        else:
            engine = Hybrid(records, index_dir=dense_index_dir(ROOT / "data/processed/dense-index"), rerank=args.strategy == "hybrid-rerank")
        if args.expand_references:
            from .references import ReferenceExpander
            if digest(articles.read_bytes()) != metadata["corpus_hash"]:
                raise ValueError("Articles hash does not match the active manifest")
            engine = ReferenceExpander(engine, read_jsonl(articles), records,
                                       review_status=metadata["review_status"])
        if args.decompose:
            from .decomposition import retrieve_multi
            if args.generator == "groq":
                from .groq_generation import GroqDecomposer
                planner = GroqDecomposer()
            else:
                planner = None
            hits, decomposition = retrieve_multi(args.question, engine, args.top_k, planner=planner)
        else:
            hits, decomposition = engine.search(args.question, args.top_k), None
        if args.generator == "extractive":
            if args.context == "fulltext":
                raise ValueError("Fulltext is a generative baseline only")
            result = extractive_answer(hits, metadata)
            supplied = pack(hits, 12000)
        elif args.generator == "local":
            from .local_generation import LocalGenerator
            supplied = pack_with_article_leads(hits, records, 7000)
            result = LocalGenerator().generate(args.question, supplied, metadata)
        elif args.generator == "groq":
            from .groq_generation import GroqGenerator
            supplied = pack_with_article_leads(hits, records, 7000)
            result = GroqGenerator().generate(args.question, supplied, metadata) if supplied else extractive_answer([], metadata)
        else:
            from .generation import GeminiGenerator
            supplied = records if args.context == "fulltext" else hits
            result = GeminiGenerator().generate(args.question, supplied, metadata)
        if decomposition:
            decomposition["context_passage_ids"] = [hit["passage_id"] for hit in supplied]
        result["decomposition"] = decomposition
    elif args.command == "evaluate":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Run ID must be a simple name of at most 80 characters")
        if args.split == "test":
            from .release import assert_reserved_test_ready
            assert_reserved_test_ready(ROOT / "runs/release-candidate/manifest.json", args.questions, manifest)
        result = evaluate(args.questions, passages, args.split, ROOT / "runs" / args.run_id,
                          args.k, args.strategy, args.context_chars)
    elif args.command == "report":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Run ID must be a simple name of at most 80 characters")
        result = report(ROOT / "runs" / args.run_id)
    elif args.command == "compare-runs":
        from .experiments import compare_runs
        for run_id in (args.left, args.right):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", run_id):
                raise ValueError("Invalid run ID")
        result = compare_runs(ROOT / "runs" / args.left, ROOT / "runs" / args.right)
    elif args.command == "select-validation":
        from .experiments import select_validation
        if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", item) for item in args.run_ids):
            raise ValueError("Invalid run ID")
        result = select_validation(args.questions, [ROOT / "runs" / item for item in args.run_ids], args.policy)
    elif args.command == "oracle-run":
        from .experiments import run_oracle
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Invalid run ID")
        metadata = json.loads(manifest.read_text())
        if digest(passages.read_bytes()) != metadata["passages_hash"]:
            raise ValueError("Passages hash does not match the active manifest")
        result = run_oracle(args.questions, passages, metadata, ROOT / "runs" / args.run_id, args.split)
    elif args.command == "bench-retrieval":
        from .benchmark import measure_retrieval
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Invalid run ID")
        result = measure_retrieval(args.questions, passages, args.strategy, args.repeat, args.concurrency)
        output = ROOT / "runs" / args.run_id / "latency.json"
        if output.exists():
            raise ValueError("Benchmark run ID already exists")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        result = {key: value for key, value in result.items() if key != "observations"}
        result["artifact"] = str(output)
    elif args.command == "bench-generation":
        from .benchmark import measure_generation_variability
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Invalid run ID")
        selection = json.loads(args.selection.read_text())
        if selection.get("split") != "dev" or selection.get("repeats") != 3:
            raise ValueError("Variability selection must be predeclared on dev with three repeats")
        metadata = json.loads(manifest.read_text())
        if digest(passages.read_bytes()) != metadata["passages_hash"]:
            raise ValueError("Passages hash does not match the active manifest")
        output = ROOT / "runs" / args.run_id / "generation_variability.json"
        if output.exists():
            raise ValueError("Benchmark run ID already exists")
        result = measure_generation_variability(args.questions, passages, metadata,
                                                 selection["selected_question_ids"])
        result["selection_sha256"] = digest(args.selection.read_bytes())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        result = {key: value for key, value in result.items() if key != "observations"}
        result["artifact"] = str(output)
    elif args.command == "calibrate-groq":
        from .groq_calibration import run_calibration
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Run ID must be a simple name of at most 80 characters")
        result = run_calibration(args.questions, passages, manifest, ROOT / "runs" / args.run_id,
                                 max_new=args.max_new, pause_seconds=args.pause_seconds)
    elif args.command == "audit-questions":
        from .question_audit import audit_questions
        result = audit_questions(args.questions, passages, json.loads(manifest.read_text())["corpus_hash"])
    elif args.command == "release-readiness":
        from .release import release_readiness
        result = release_readiness(args.questions, manifest, args.selection, args.systems)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        result["manifest"] = str(args.output)
    elif args.command == "test-preflight":
        from .release import assert_reserved_test_ready
        result = assert_reserved_test_ready(args.release_manifest, args.questions, manifest)
    elif args.command == "run-reserved-test":
        from .release import assert_reserved_test_ready, run_reserved_test
        from .campaign import build_runners
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.run_id):
            raise ValueError("Invalid run ID")
        frozen = assert_reserved_test_ready(args.release_manifest, args.questions, manifest)
        if digest(args.systems.read_bytes()) != frozen["systems_sha256"]:
            raise ValueError("System specification differs from the release freeze")
        runners = build_runners(passages, manifest, args.systems, articles)
        result = run_reserved_test(args.release_manifest, args.questions, manifest,
                                   ROOT / "runs" / args.run_id, runners)
    elif args.command == "blind-packets":
        from .release import assert_reserved_test_ready
        from .judgments import prepare_blind_packets
        assert_reserved_test_ready(args.release_manifest, args.questions, manifest)
        result = prepare_blind_packets(args.questions, {"fulltext": args.fulltext,
            "bm25_rag": args.bm25_rag, "selected_pipeline": args.selected_pipeline}, args.output)
    elif args.command == "score-judgments":
        from .judgments import score_judgments
        result = score_judgments(args.mapping, args.judgments, args.replications, args.seed)
    elif args.command == "reproduce-retrieval":
        from .reproduction import reproduce_retrieval
        if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", item) for item in args.run_ids):
            raise ValueError("Invalid run ID")
        result = reproduce_retrieval(args.questions, passages, [ROOT / "runs" / item for item in args.run_ids])
    elif args.command == "publication-audit":
        from .reproduction import publication_audit
        result = publication_audit()
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
