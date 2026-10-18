"""Bounded multi-evidence retrieval; the original question is always searched."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from .generation import GenerationError
from .local_generation import LocalGenerator, LOCAL_MODEL_SLOTS
from .retrieval import ARTICLE_LIST, ARTICLE_QUERY, explicit_article_numbers, rrf

PLAN_VERSION = "fr-multi-evidence-v1"
PLAN_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"subquestions": {"type": "array", "minItems": 1, "maxItems": 2,
                                    "items": {"type": "string"}}},
    "required": ["subquestions"]
}

def explicit_plan(question: str) -> list[str] | None:
    articles = explicit_article_numbers(question)
    if len(articles) < 2:
        return None
    remainder = ARTICLE_LIST.sub(" ", question)
    remainder = ARTICLE_QUERY.sub(" ", remainder)
    remainder = re.sub(r"\s+", " ", remainder).strip(" ,;:?.!")
    if len(remainder.split()) < 3:
        remainder = ""
    return [f"article {number} {remainder}".strip() for number in articles[:2]]

class LocalDecomposer:
    """Ask the loopback Qwen server for at most two auxiliary searches."""
    method = "local_qwen"
    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int = 60):
        settings = LocalGenerator(base_url=base_url, model=model, timeout=timeout)
        self.base_url = settings.base_url
        self.model = settings.model
        self.timeout = timeout

    def plan(self, question: str) -> tuple[list[str], dict | None]:
        if not question.strip() or len(question) > 2000:
            raise ValueError("Question length must be between 1 and 2000 characters")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Tu prépares uniquement la recherche documentaire dans la Constitution marocaine de 2011. Ne réponds pas à la question. N'invente aucun fait. Ne change pas l'intention de l'utilisateur."},
                {"role": "user", "content": f"/no_think\nQuestion originale : {question}\nPropose une ou deux sous-questions courtes et complémentaires pour trouver les preuves nécessaires. Retourne uniquement l'objet JSON demandé."}
            ],
            "temperature": 0.0, "max_tokens": 256, "stream": False,
            "response_format": {"type": "json_schema", "schema": PLAN_SCHEMA}
        }
        request = Request(self.base_url + "/v1/chat/completions",
                          data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        if not LOCAL_MODEL_SLOTS.acquire(blocking=False):
            raise GenerationError("local_provider_busy")
        try:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    result = json.load(response)
            except (HTTPError, URLError, TimeoutError) as exc:
                raise GenerationError(f"local_planner_unavailable: {exc}") from exc
        finally:
            LOCAL_MODEL_SLOTS.release()
        try:
            raw = json.loads(result["choices"][0]["message"]["content"])
            subquestions = raw["subquestions"]
            if not isinstance(subquestions, list) or not 1 <= len(subquestions) <= 2:
                raise ValueError("Expected one or two subquestions")
            if any(not isinstance(item, str) or not item.strip() or len(item) > 300 for item in subquestions):
                raise ValueError("Invalid subquestion")
            subquestions = [item.strip() for item in subquestions]
            if len({question.casefold(), *(item.casefold() for item in subquestions)}) != len(subquestions) + 1:
                raise ValueError("Duplicate or unchanged subquestion")
            return subquestions, result.get("usage")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise GenerationError(f"invalid_plan: {exc}") from exc

def retrieve_multi(question: str, engine, k: int = 5, planner: LocalDecomposer | None = None) -> tuple[list[dict], dict]:
    if not question.strip() or k < 2:
        raise ValueError("Multi-evidence search requires a question and k >= 2")
    started = time.perf_counter()
    subquestions = explicit_plan(question)
    if subquestions is None:
        active_planner = planner or LocalDecomposer()
        subquestions, usage = active_planner.plan(question)
        method = getattr(active_planner, "method", "local_qwen")
    else:
        usage = None
        method = "explicit_articles"
    queries = [question, *subquestions]
    if len(queries) > 3:
        raise ValueError("Retrieval call budget exceeded")
    planning_seconds = time.perf_counter() - started
    lists = [engine.search(query, k) for query in queries]
    matched = {}
    for index, hits in enumerate(lists):
        for hit in hits:
            matched.setdefault(hit["passage_id"], []).append(index)
    chosen, seen = [], set()
    for hits in lists:
        if hits and hits[0]["passage_id"] not in seen:
            chosen.append(hits[0])
            seen.add(hits[0]["passage_id"])
    for hit in rrf(lists, k=k * len(lists)):
        if hit["passage_id"] not in seen:
            chosen.append(hit)
            seen.add(hit["passage_id"])
    selected = [{**hit, "rank": rank, "matched_query_indexes": matched[hit["passage_id"]]}
                for rank, hit in enumerate(chosen[:k], 1)]
    trace = {"method": method, "plan_version": PLAN_VERSION, "subquestions": subquestions,
             "retrieval_calls": len(queries), "planning_usage": usage,
             "planning_model_calls": int(method in {"local_qwen", "groq_model"}),
             "planning_seconds": round(planning_seconds, 4),
             "total_seconds": round(time.perf_counter() - started, 4),
             "plan_review_status": "unverified_semantic" if method in {"local_qwen", "groq_model"} else "explicit_article_refs",
             "candidate_passage_ids": [hit["passage_id"] for hits in lists for hit in hits],
             "selected_passage_ids": [hit["passage_id"] for hit in selected]}
    return selected, trace
