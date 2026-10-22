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


def score_review_verdicts(packet_path: Path, mapping_path: Path, reviewed_path: Path,
                          replications: int = 2000, seed: int = 20261018) -> dict:
    """Score a categorical blind review without inventing four-criterion labels.

    Clean success requires a fully correct answer or a justified abstention.
    A response with minor issues may be acceptable, but is not clean success.
    Technical errors score zero on both measures.
    """
    if not 100 <= replications <= 10000:
        raise ValueError("Bootstrap replications must be between 100 and 10000")
    packets = read_jsonl(packet_path)
    mapping = read_jsonl(mapping_path)
    reviews = read_jsonl(reviewed_path)
    packet_by_id = {row["blind_id"]: row for row in packets}
    mapping_by_id = {row["blind_id"]: row for row in mapping}
    review_by_id = {row["blind_id"]: row for row in reviews}
    if (len(packet_by_id) != len(packets) or len(mapping_by_id) != len(mapping)
            or len(review_by_id) != len(reviews) or set(packet_by_id) != set(mapping_by_id)):
        raise ValueError("Blind packet and mapping IDs are incomplete or duplicated")
    nontechnical = {blind_id for blind_id, row in mapping_by_id.items()
                    if not row["technical_error"]}
    if set(review_by_id) != nontechnical:
        raise ValueError("Reviews must cover exactly the responses without technical errors")

    allowed = {"correct", "correct_minor_issues", "abstention_correct",
               "partially_correct", "incorrect", "non_answer", "abstention_wrong"}
    clean = {"correct", "abstention_correct"}
    acceptable = clean | {"correct_minor_issues"}
    systems = sorted({row["system"] for row in mapping})
    if systems != ["bm25_rag", "fulltext", "selected_pipeline"]:
        raise ValueError("Expected exactly the three frozen final systems")
    families = sorted({row["family_id"] for row in mapping})
    if any(sum(row["system"] == system and row["family_id"] == family
               for row in mapping) != 1 for system in systems for family in families):
        raise ValueError("Each system must cover every family exactly once")

    values = {system: {} for system in systems}
    summaries = {}
    for system in systems:
        rows = [row for row in mapping if row["system"] == system]
        verdict_counts = {verdict: 0 for verdict in sorted(allowed)}
        technical = answered = clean_count = acceptable_count = unacceptable_answers = 0
        for meta in rows:
            blind_id = meta["blind_id"]
            packet = packet_by_id[blind_id]
            if (packet["question_id"] != meta["question_id"] or
                    packet["family_id"] != meta["family_id"] or
                    packet["technical_error"] != meta["technical_error"] or
                    packet["status"] != meta["status"]):
                raise ValueError(f"Packet and mapping disagree for {blind_id}")
            if meta["technical_error"]:
                technical += 1
                values[system][meta["family_id"]] = {"clean": 0, "acceptable": 0}
                continue
            reviewed = review_by_id[blind_id]
            if {key: value for key, value in reviewed.items() if key != "review"} != packet:
                raise ValueError(f"Reviewed response differs from blind packet: {blind_id}")
            judgment = reviewed.get("review")
            verdict = judgment.get("verdict") if isinstance(judgment, dict) else None
            if verdict not in allowed or type(judgment.get("acceptable")) is not bool:
                raise ValueError(f"Invalid review verdict for {blind_id}")
            if judgment["acceptable"] != (verdict in acceptable):
                raise ValueError(f"Verdict and acceptability disagree for {blind_id}")
            if any(type(judgment.get(key)) is not bool for key in
                   ("quotes_verified_against_pdf", "citation_metadata_ok")):
                raise ValueError(f"Missing citation review flags for {blind_id}")
            if verdict.startswith("abstention_") != (meta["status"] == "insufficient_evidence"):
                raise ValueError(f"Verdict and answer status disagree for {blind_id}")
            is_answered = meta["status"] in {"answered", "partially_answered"}
            answered += is_answered
            verdict_counts[verdict] += 1
            clean_count += verdict in clean
            acceptable_count += judgment["acceptable"]
            unacceptable_answers += is_answered and not judgment["acceptable"]
            values[system][meta["family_id"]] = {
                "clean": int(verdict in clean), "acceptable": int(judgment["acceptable"])}
        summaries[system] = {
            "questions": len(rows), "technical_errors": technical,
            "clean_success": clean_count / len(rows), "clean_success_n": clean_count,
            "acceptable": acceptable_count / len(rows), "acceptable_n": acceptable_count,
            "substantive_coverage": answered / len(rows), "answered_n": answered,
            "unacceptable_among_answers": unacceptable_answers / answered if answered else None,
            "unacceptable_answers_n": unacceptable_answers,
            "verdict_counts": {key: value for key, value in verdict_counts.items() if value}}

    randomizer = random.Random(seed)
    paired = {}
    for metric in ("clean", "acceptable"):
        for index, left in enumerate(systems):
            for right in systems[index + 1:]:
                differences = {family: values[right][family][metric] - values[left][family][metric]
                               for family in families}
                samples = sorted(sum(differences[randomizer.choice(families)] for _ in families)
                                 / len(families) for _ in range(replications))
                paired[f"{right}-minus-{left}:{metric}"] = {
                    "n_families": len(families),
                    "delta": sum(differences.values()) / len(families),
                    "ci95": [samples[int(.025 * (replications - 1))],
                             samples[int(.975 * (replications - 1))]]}
    return {"systems": summaries, "paired": paired, "families": len(families),
            "replications": replications, "seed": seed,
            "clean_rule": "correct or abstention_correct; technical errors fail",
            "acceptable_rule": "correct, correct_minor_issues, or abstention_correct; technical errors fail",
            "risk_note": "Four separate semantic criteria were not supplied; prior risk_among_answers is not recomputed",
            "packets_sha256": digest(packet_path.read_bytes()),
            "mapping_sha256": digest(mapping_path.read_bytes()),
            "reviews_sha256": digest(reviewed_path.read_bytes())}
