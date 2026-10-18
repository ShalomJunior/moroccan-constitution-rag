"""Structural checks for the French question benchmark; never judge legal truth."""
from collections import Counter

from .store import read_jsonl

EXPECTED = {"dev": 45, "validation": 45, "test": 90}
ANSWERABLE = {"answered", "partially_answered"}
STATUSES = ANSWERABLE | {"needs_clarification", "insufficient_evidence", "out_of_scope"}
CATEGORIES = {"direct", "conceptual", "multi_evidence", "false_premise", "ambiguous", "out_of_scope"}


def audit_questions(questions_path, passages_path, corpus_hash):
    """Return inventory and defects. A clean audit is not a human review."""
    questions = read_jsonl(questions_path) if questions_path.exists() else []
    passages = {p["passage_id"]: p for p in read_jsonl(passages_path)} if passages_path.exists() else {}
    problems = []
    counts = Counter()
    categories = Counter()
    seen_ids = set()
    families = {}
    for position, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            problems.append(f"row-{position}: question must be an object")
            continue
        qid = q.get("question_id") or f"row-{position}"
        split = q.get("split")
        family = q.get("family_id")
        if qid in seen_ids:
            problems.append(f"{qid}: duplicate question_id")
        seen_ids.add(qid)
        if split not in EXPECTED:
            problems.append(f"{qid}: invalid split")
        else:
            counts[split] += 1
        if not isinstance(family, str) or not family.strip():
            problems.append(f"{qid}: missing family_id")
        elif family in families and families[family] != split:
            problems.append(f"{qid}: family crosses splits")
        else:
            families[family] = split
        if q.get("language") != "fr" or not isinstance(q.get("question"), str) or not q["question"].strip():
            problems.append(f"{qid}: French question is missing")
        if q.get("review_status") != "reviewed":
            problems.append(f"{qid}: human annotation is not reviewed")
            continue
        if q.get("corpus_hash") != corpus_hash:
            problems.append(f"{qid}: corpus hash differs")
        category = q.get("category")
        if not isinstance(category, str) or category not in CATEGORIES:
            problems.append(f"{qid}: category is missing or invalid")
        else:
            categories[category] += 1
        if not isinstance(q.get("theme"), str) or not q["theme"].strip():
            problems.append(f"{qid}: theme is missing")
        status = q.get("expected_status")
        alternatives = q.get("acceptable_statuses")
        if not isinstance(status, str) or status not in STATUSES or not isinstance(alternatives, list) or status not in alternatives or any(
                not isinstance(alternative, str) or alternative not in STATUSES for alternative in alternatives):
            problems.append(f"{qid}: expected or acceptable status is invalid")
        for field in ("required_claims", "forbidden_inferences", "relevant_articles", "relevant_spans"):
            if not isinstance(q.get(field), list):
                problems.append(f"{qid}: {field} must be a list")
        if not isinstance(q.get("annotator"), str) or not q["annotator"].strip():
            problems.append(f"{qid}: annotator is missing")
        if not isinstance(q.get("source_edition"), str) or not q["source_edition"].strip():
            problems.append(f"{qid}: source edition is missing")
        if not isinstance(q.get("annotation_version"), (str, int)):
            problems.append(f"{qid}: annotation version is missing")
        groups = q.get("acceptable_evidence_sets")
        if status in ANSWERABLE and (not isinstance(groups, list) or not groups or any(
                not isinstance(group, list) or not group for group in groups)):
            problems.append(f"{qid}: sufficient evidence sets are missing")
        if status in ANSWERABLE and not q.get("required_claims"):
            problems.append(f"{qid}: required claims are missing")
        spans = list(q.get("relevant_spans")) if isinstance(q.get("relevant_spans"), list) else []
        if isinstance(groups, list):
            spans += [span for group in groups if isinstance(group, list) for span in group]
        for span in spans:
            if not isinstance(span, dict):
                problems.append(f"{qid}: invalid evidence span")
                continue
            passage = passages.get(span.get("passage_id"))
            start, end = span.get("char_start"), span.get("char_end")
            if (passage is None or type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(passage["canonical_text"])):
                problems.append(f"{qid}: evidence span is outside the current corpus")
            elif passage.get("article_number") not in (q.get("relevant_articles")
                                                         if isinstance(q.get("relevant_articles"), list) else []):
                problems.append(f"{qid}: evidence article is absent from relevant_articles")
    for split, expected in EXPECTED.items():
        actual = len({q.get("family_id") for q in questions if isinstance(q, dict) and q.get("split") == split})
        if actual != expected:
            problems.append(f"{split}: {actual}/{expected} question families")
    return {"status": "structurally_complete" if not problems else "incomplete",
            "question_count": len(questions), "family_counts": {split: len({q.get("family_id") for q in questions
                if isinstance(q, dict) and q.get("split") == split}) for split in EXPECTED},
            "reviewed_count": sum(isinstance(q, dict) and q.get("review_status") == "reviewed" for q in questions),
            "category_counts": dict(categories), "problems": problems}
