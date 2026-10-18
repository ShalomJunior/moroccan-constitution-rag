"""Blind response packets and family-paired statistics from finalized human labels."""
import json
import random
from pathlib import Path
from .store import digest, read_jsonl, write_jsonl


def prepare_blind_packets(questions_path: Path, answer_runs: dict[str, Path],
                          output_dir: Path, seed: int = 20261018, expected_families: int = 90) -> dict:
    questions = [q for q in read_jsonl(questions_path) if q.get("split") == "test"]
    by_id = {q["question_id"]: q for q in questions}
    if len(by_id) != len(questions) or len({q["family_id"] for q in questions}) != expected_families:
        raise ValueError("Blind packets need the frozen reserved questions")
    if any(q.get("review_status") != "reviewed" for q in questions):
        raise ValueError("Blind packets need reviewed test questions")
    if set(answer_runs) != {"fulltext", "bm25_rag", "selected_pipeline"}:
        raise ValueError("Blind packets need exactly the three final systems")
    packet_rows, mapping_rows = [], []
    for system, path in answer_runs.items():
        rows = read_jsonl(path)
        answers = {row["question_id"]: row for row in rows}
        if len(answers) != len(rows) or set(answers) != set(by_id):
            raise ValueError(f"Run {system} is incomplete or has duplicate IDs")
        for qid, row in answers.items():
            answer = row.get("answer") or {}
            status = answer.get("status", "technical_error" if row.get("error") else "missing")
            sources = [{key: source.get(key) for key in ("passage_id", "article_number", "page_spans", "source_url")}
                       for source in answer.get("sources", [])]
            packet_rows.append({"question_id": qid, "family_id": by_id[qid]["family_id"],
                                "question": by_id[qid]["question"], "status": status,
                                "claims": answer.get("claims", []), "sources": sources,
                                "limitations": answer.get("limitations", ""),
                                "technical_error": bool(row.get("error"))})
            mapping_rows.append({"question_id": qid, "family_id": by_id[qid]["family_id"],
                                 "system": system, "status": status,
                                 "technical_error": bool(row.get("error")),
                                 "elapsed_ms": row.get("elapsed_ms"), "usage": answer.get("usage"),
                                 "confidence": row.get("confidence")})
    order = list(range(len(packet_rows)))
    random.Random(seed).shuffle(order)
    packets, mapping = [], []
    for number, index in enumerate(order, 1):
        blind_id = f"B{number:04d}"
        packets.append({"blind_id": blind_id, **packet_rows[index]})
        mapping.append({"blind_id": blind_id, **mapping_rows[index]})
    output_dir.mkdir(parents=True, exist_ok=True)
    packet_path, mapping_path = output_dir / "packets.jsonl", output_dir / "private_mapping.jsonl"
    if packet_path.exists() or mapping_path.exists():
        raise ValueError("Blind packet output already exists; use a new directory")
    write_jsonl(packet_path, packets)
    write_jsonl(mapping_path, mapping)
    return {"packets": len(packets), "families": expected_families, "seed": seed,
            "packets_sha256": digest(packet_path.read_bytes()), "mapping_sha256": digest(mapping_path.read_bytes())}


def score_judgments(mapping_path: Path, judgments_path: Path, replications: int = 2000,
                    seed: int = 20261018) -> dict:
    if not 100 <= replications <= 10000:
        raise ValueError("Bootstrap replications must be between 100 and 10000")
    mapping = read_jsonl(mapping_path)
    judgments = read_jsonl(judgments_path)
    mapped = {row["blind_id"]: row for row in mapping}
    judged = {row["blind_id"]: row for row in judgments}
    if len(mapped) != len(mapping) or len(judged) != len(judgments) or set(mapped) != set(judged):
        raise ValueError("Missing or duplicate finalized judgments")
    systems = sorted({row["system"] for row in mapping})
    families = sorted({row["family_id"] for row in mapping})
    scored = {system: {} for system in systems}
    for blind_id, meta in mapped.items():
        label = judged[blind_id]
        required = ("decision_ok", "faithful", "complete", "citations_ok", "unsupported_or_incorrect")
        if label.get("finalized") is not True or any(type(label.get(key)) is not bool for key in required):
            raise ValueError(f"Judgment {blind_id} is not finalized")
        if meta["technical_error"]:
            value = 0
        else:
            value = int(all(label[key] for key in required[:-1]) and not label["unsupported_or_incorrect"])
        scored[meta["system"]].setdefault(meta["family_id"], []).append(value)
    if any(set(rows) != set(families) for rows in scored.values()):
        raise ValueError("Systems do not cover identical families")
    summaries = {}
    for system in systems:
        meta_rows = [row for row in mapping if row["system"] == system]
        valid = [value for values in scored[system].values() for value in values]
        answered = [row for row in meta_rows if not row["technical_error"]
                    and row["status"] in {"answered", "partially_answered"}]
        risky = [row for row in answered if judged[row["blind_id"]]["unsupported_or_incorrect"]]
        summaries[system] = {"questions": len(meta_rows), "technical_errors": sum(row["technical_error"] for row in meta_rows),
                             "strict_success": sum(valid) / len(valid) if valid else None,
                             "strict_success_n": len(valid), "coverage": len(answered) / len(meta_rows),
                             "answered_n": len(answered), "risk_among_answers": len(risky) / len(answered) if answered else None,
                             "risk_n": len(answered),
                             "elapsed_ms_total": round(sum(row["elapsed_ms"] for row in meta_rows
                                                           if isinstance(row.get("elapsed_ms"), (int, float))), 1)}
        confidence_rows = [row for row in answered if isinstance(row.get("confidence"), (int, float))
                           and 0 <= row["confidence"] <= 1]
        if len(confidence_rows) == len(answered) and answered:
            curve = []
            for threshold in sorted({0.0, *(row["confidence"] for row in confidence_rows)}):
                accepted = [row for row in confidence_rows if row["confidence"] >= threshold]
                curve.append({"threshold": threshold, "coverage": len(accepted) / len(meta_rows),
                              "risk": sum(judged[row["blind_id"]]["unsupported_or_incorrect"] for row in accepted) / len(accepted)
                              if accepted else None, "answered_n": len(accepted)})
            summaries[system]["risk_coverage_curve"] = curve
    randomizer = random.Random(seed)
    paired = {}
    for left_index, left in enumerate(systems):
        for right in systems[left_index + 1:]:
            eligible = [family for family in families
                        if all(value is not None for value in scored[left][family] + scored[right][family])]
            if not eligible:
                paired[f"{right}-minus-{left}"] = {"n_families": 0, "delta": None, "ci95": None}
                continue
            differences = {family: (sum(scored[right][family]) / len(scored[right][family]) -
                                    sum(scored[left][family]) / len(scored[left][family])) for family in eligible}
            samples = sorted(sum(differences[randomizer.choice(eligible)] for _ in eligible) / len(eligible)
                             for _ in range(replications))
            paired[f"{right}-minus-{left}"] = {"n_families": len(eligible),
                                                 "delta": sum(differences.values()) / len(eligible),
                                                 "ci95": [samples[int(.025 * (replications - 1))],
                                                          samples[int(.975 * (replications - 1))]]}
    return {"systems": summaries, "paired_strict_success": paired,
            "families": len(families), "replications": replications, "seed": seed,
            "mapping_sha256": digest(mapping_path.read_bytes()),
            "judgments_sha256": digest(judgments_path.read_bytes())}
