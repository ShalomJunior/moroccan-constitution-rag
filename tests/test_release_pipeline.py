import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from constitution_evidence.benchmark import measure_retrieval, measure_generation_variability
from constitution_evidence.judgments import prepare_blind_packets, score_judgments
from constitution_evidence.release import release_readiness, assert_reserved_test_ready, run_reserved_test
from constitution_evidence.store import read_jsonl, write_jsonl


class ReleasePipelineTests(unittest.TestCase):
    def test_latency_and_variability_use_development_questions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions, passages = root / "questions.jsonl", root / "passages.jsonl"
            write_jsonl(questions, [{"question_id": "q1", "family_id": "f1", "split": "dev",
                                     "question": "article 20 droit à la vie"}])
            write_jsonl(passages, [{"passage_id": "p1", "article_number": 20,
                                    "paragraph_index": 1, "canonical_text": "Le droit à la vie.",
                                    "text_hash": "hash", "page_spans": [2]}])
            timing = measure_retrieval(questions, passages, repeat=3, concurrency=2)
            self.assertEqual(timing["calls"], 4)
            self.assertEqual(timing["errors"], 0)
            class Model:
                model = "fake-qwen"
                calls = 0
                def generate(self, question, context, manifest):
                    self.calls += 1
                    return {"status": "partially_answered", "claims": [], "sources": [],
                            "limitations": "", "usage": {"total_tokens": self.calls}}
            model = Model()
            varied = measure_generation_variability(questions, passages, {}, ["q1"], model)
            self.assertEqual(varied["calls"], 3)
            self.assertEqual(varied["variation"]["q1"]["distinct_answer_hashes"], 1)
            self.assertEqual(varied["token_totals"]["total_tokens"], 6)

    def test_release_blocks_unreviewed_corpus_and_reserved_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, questions = root / "corpus.json", root / "questions.jsonl"
            corpus.write_text(json.dumps({"corpus_hash": "abc", "review_status": "unreviewed_ocr"}))
            write_jsonl(questions, [{"question_id": "q1", "family_id": "f1", "split": "test",
                                     "review_status": "author_provisional", "corpus_hash": "abc"}])
            readiness = release_readiness(questions, corpus, root / "selection.json", root / "systems.json",
                                          repo_root=root)
            self.assertEqual(readiness["status"], "blocked")
            frozen = root / "release.json"
            frozen.write_text(json.dumps(readiness))
            with self.assertRaisesRegex(ValueError, "ready release"):
                assert_reserved_test_ready(frozen, questions, corpus)

    def test_release_rejects_pipeline_that_differs_from_validation_winner(self):
        from constitution_evidence.campaign import prompt_hash
        from constitution_evidence.store import digest
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "configs").mkdir()
            (root / "runs/winner").mkdir(parents=True)
            (root / "data/annotations").mkdir(parents=True)
            (root / "data/processed").mkdir(parents=True)
            questions = root / "questions.jsonl"
            write_jsonl(questions, [])
            passages = root / "data/processed/passages.jsonl"
            write_jsonl(passages, [])
            corpus = root / "data/processed/manifest.json"
            corpus.write_text(json.dumps({"corpus_hash": "c", "review_status": "reviewed"}))
            (root / "data/annotations/corpus-review.jsonl").write_text("")
            policy = root / "configs/selection_policy.json"
            policy.write_text("{}")
            selection = root / "runs/validation-selection.json"
            selection.write_text(json.dumps({"status": "ready_for_retrieval_selection",
                                             "selected_retrieval_run": "winner",
                                             "questions_sha256": digest(questions.read_bytes()),
                                             "policy_sha256": digest(policy.read_bytes()),
                                             "candidates": [{"run": "winner", "method": "hybrid"}]}))
            (root / "runs/winner/manifest.json").write_text(json.dumps({
                "method": "hybrid", "article_k": 10, "context_chars": 7000,
                "questions_sha256": digest(questions.read_bytes()),
                "passages_sha256": digest(passages.read_bytes())}))
            systems = root / "configs/final_systems.json"
            systems.write_text(json.dumps({
                "fulltext": {"model": "Qwen", "prompt_sha256": prompt_hash(), "context_mode": "fulltext"},
                "bm25_rag": {"model": "Qwen", "prompt_sha256": prompt_hash(), "strategy": "bm25"},
                "selected_pipeline": {"model": "Qwen", "prompt_sha256": prompt_hash(),
                                      "strategy": "dense", "top_k": 10, "max_context_chars": 7000}}))
            result = release_readiness(questions, corpus, selection, systems, repo_root=root)
            self.assertIn("Final pipeline differs from the selected validation run", result["reasons"])

    def test_blinding_and_family_paired_statistics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions = root / "questions.jsonl"
            write_jsonl(questions, [{"question_id": f"q{n}", "family_id": f"f{n}", "split": "test",
                                     "question": f"Question {n}", "review_status": "reviewed"} for n in (1, 2)])
            runs = {}
            for system in ("fulltext", "bm25_rag", "selected_pipeline"):
                path = root / f"{system}.jsonl"
                write_jsonl(path, [{"question_id": f"q{n}", "family_id": f"f{n}", "elapsed_ms": 10,
                                    "confidence": .8, "answer": {"status": "answered", "claims": [{"text": "Réponse"}],
                                    "sources": [{"passage_id": "p1", "retriever": system}],
                                    "model": system, "limitations": ""},
                                    "error": {"type": "TimeoutError"} if system == "fulltext" and n == 2 else None}
                                   for n in (1, 2)])
                runs[system] = path
            result = prepare_blind_packets(questions, runs, root / "blind", expected_families=2)
            self.assertEqual(result["packets"], 6)
            packets = read_jsonl(root / "blind/packets.jsonl")
            self.assertTrue(all("system" not in json.dumps(row) and "retriever" not in json.dumps(row) for row in packets))
            mapping = read_jsonl(root / "blind/private_mapping.jsonl")
            labels = [{"blind_id": row["blind_id"], "finalized": True, "decision_ok": True,
                       "faithful": row["system"] != "fulltext", "complete": True,
                       "citations_ok": True, "unsupported_or_incorrect": row["system"] == "fulltext"}
                      for row in mapping]
            labels_path = root / "judgments.jsonl"
            write_jsonl(labels_path, labels)
            scored = score_judgments(root / "blind/private_mapping.jsonl", labels_path, replications=100)
            self.assertEqual(scored["systems"]["bm25_rag"]["strict_success"], 1)
            self.assertEqual(scored["systems"]["fulltext"]["risk_among_answers"], 1)
            self.assertEqual(scored["systems"]["fulltext"]["technical_errors"], 1)
            self.assertEqual(scored["systems"]["fulltext"]["strict_success_n"], 2)
            self.assertEqual(scored["families"], 2)
            with self.assertRaises(ValueError):
                prepare_blind_packets(questions, runs, root / "blind", expected_families=2)

    def test_reserved_run_resumes_without_duplicate_model_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            questions = root / "questions.jsonl"
            corpus = root / "corpus.json"
            frozen = root / "release.json"
            passages = root / "passages.jsonl"
            write_jsonl(questions, [{"question_id": "q1", "family_id": "f1", "split": "test",
                                     "review_status": "reviewed", "question": "Question ?"}])
            write_jsonl(passages, [{"passage_id": "p1", "canonical_text": "Texte.", "text_hash": "hash"}])
            from constitution_evidence.store import digest
            corpus.write_text(json.dumps({"passages_hash": digest(passages.read_bytes())}))
            frozen.write_text('{"status":"ready"}')
            calls = []
            def runner(question):
                calls.append(question)
                return {"answer": {"status": "insufficient_evidence", "claims": [], "sources": []},
                        "context_passage_ids": ["p1"]}
            systems = {name: runner for name in ("fulltext", "bm25_rag", "selected_pipeline")}
            with patch("constitution_evidence.release.assert_reserved_test_ready", return_value={"status": "ready"}):
                first = run_reserved_test(frozen, questions, corpus, root / "run", systems, expected_families=1)
                second = run_reserved_test(frozen, questions, corpus, root / "run", systems, expected_families=1)
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
