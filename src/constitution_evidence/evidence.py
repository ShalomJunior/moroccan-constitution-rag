"""Context packing and exact citation validation."""
from .store import digest

STATUSES = {"answered", "partially_answered", "needs_clarification", "insufficient_evidence", "out_of_scope"}

def pack(hits: list[dict], max_chars: int = 12000) -> list[dict]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    chosen, used = [], 0
    for hit in hits:
        size = len(hit["canonical_text"])
        if used + size <= max_chars:
            chosen.append(hit)
            used += size
    return chosen


def pack_with_article_leads(hits: list[dict], passages: list[dict], max_chars: int = 7000) -> list[dict]:
    """Preserve ranked hits and include nearby paragraphs needed for legal context."""
    chosen = pack(hits, max_chars)
    by_position = {(p["article_number"], p["paragraph_index"]): p for p in passages}
    seen = {p["passage_id"] for p in chosen}
    extra, used = {}, sum(len(p["canonical_text"]) for p in chosen)
    for hit in chosen:
        article, paragraph = hit["article_number"], hit["paragraph_index"]
        # The opening identifies the subject of a list; the following paragraph
        # often holds a qualification or exception omitted by a top hit.
        positions = [1, paragraph + 1]
        if paragraph == 1:
            positions = [2]
        for position in positions:
            neighbor = by_position.get((article, position))
            if neighbor and neighbor["passage_id"] not in seen and used + len(neighbor["canonical_text"]) <= max_chars:
                extra[neighbor["passage_id"]] = {**neighbor, "retriever": "article_context"}
                seen.add(neighbor["passage_id"])
                used += len(neighbor["canonical_text"])
    result, inserted = [], set()
    for hit in chosen:
        lead = by_position.get((hit["article_number"], 1))
        if lead and lead["passage_id"] in extra and lead["passage_id"] not in inserted:
            result.append(extra[lead["passage_id"]])
            inserted.add(lead["passage_id"])
        result.append(hit)
        next_passage = by_position.get((hit["article_number"], hit["paragraph_index"] + 1))
        if next_passage and next_passage["passage_id"] in extra and next_passage["passage_id"] not in inserted:
            result.append(extra[next_passage["passage_id"]])
            inserted.add(next_passage["passage_id"])
    return result

def validate_answer(answer: dict, supplied: list[dict]) -> dict:
    if answer.get("status") not in STATUSES:
        raise ValueError("Unknown answer status")
    permitted = {p["passage_id"]: p for p in supplied}
    for claim in answer.get("claims", []):
        if not isinstance(claim.get("text"), str) or not claim.get("evidence_spans"):
            raise ValueError("A factual claim needs text and evidence")
        for evidence in claim["evidence_spans"]:
            passage = permitted.get(evidence.get("passage_id"))
            if not passage:
                raise ValueError("Citation is not in the supplied context")
            if evidence.get("source_hash") != passage["text_hash"]:
                raise ValueError("Citation hash mismatch")
            start, end = evidence.get("char_start"), evidence.get("char_end")
            if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(passage["canonical_text"])):
                raise ValueError("Citation offsets invalid")
            if passage["canonical_text"][start:end] != evidence.get("quote"):
                raise ValueError("Citation quote mismatch")
    return answer

def extractive_answer(hits: list[dict], manifest: dict, max_chars: int = 12000) -> dict:
    supplied = pack(hits, max_chars)
    if not supplied:
        return {"status": "insufficient_evidence", "claims": [], "limitations": "Aucun passage trouvé dans le corpus.", "sources": []}
    claims = []
    for hit in supplied[:5]:
        quote = hit["canonical_text"].strip()
        if len(quote) > 800:
            quote = quote[:800].rsplit(" ", 1)[0]
        start = hit["canonical_text"].find(quote)
        claims.append({"text": quote, "evidence_spans": [{"passage_id": hit["passage_id"], "char_start": start,
            "char_end": start + len(quote), "quote": quote, "source_hash": hit["text_hash"]}], "support_status": "verbatim"})
    answer = {"status": "partially_answered", "claims": claims,
              "limitations": "Extraits retrouvés automatiquement ; leur pertinence et l'exhaustivité de la réponse ne sont pas vérifiées.",
              "sources": [{"passage_id": h["passage_id"], "article_number": h["article_number"],
                           "page_spans": h["page_spans"], "source_url": manifest["source_url"],
                           "retriever": h.get("retriever"), "reference": h.get("reference")}
                          for h in supplied[:5]]}
    return validate_answer(answer, supplied)
