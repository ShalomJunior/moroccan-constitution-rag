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
    for hit in supplied[:3]:
        quote = hit["canonical_text"].strip()
        if len(quote) > 800:
            quote = quote[:800].rsplit(" ", 1)[0]
        start = hit["canonical_text"].find(quote)
        claims.append({"text": quote, "evidence_spans": [{"passage_id": hit["passage_id"], "char_start": start,
            "char_end": start + len(quote), "quote": quote, "source_hash": hit["text_hash"]}], "support_status": "verbatim"})
    answer = {"status": "partially_answered", "claims": claims,
              "limitations": "Extraits retrouvés automatiquement ; leur pertinence et l'exhaustivité de la réponse ne sont pas vérifiées.",
              "sources": [{"passage_id": h["passage_id"], "article_number": h["article_number"],
                           "page_spans": h["page_spans"], "source_url": manifest["source_url"]} for h in supplied[:3]]}
    return validate_answer(answer, supplied)
