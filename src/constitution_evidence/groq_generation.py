"""Hosted open-weight generation through Groq's maintained Python SDK."""
import json
import os

from .generation import GenerationError, PROMPT_VERSION
from .local_generation import RAW_SCHEMA, answer_messages, checked_answer

DEFAULT_MODEL = "openai/gpt-oss-20b"
GROQ_PROMPT_VERSION = PROMPT_VERSION + "-groq-v1"


def _client():
    try:
        from dotenv import load_dotenv
        from groq import Groq
    except ImportError as exc:
        raise GenerationError("groq_sdk_missing: install the groq extra") from exc
    from .store import ROOT
    load_dotenv(ROOT / ".env", override=False)
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise GenerationError("groq_api_key_missing: set GROQ_API_KEY in the server environment")
    return Groq(api_key=key, timeout=60.0, max_retries=0)


def _complete(client, **kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as exc:
        try:
            from groq import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
        except ImportError:
            raise
        if isinstance(exc, RateLimitError):
            raise GenerationError("groq_rate_limited") from exc
        if isinstance(exc, APIStatusError) and exc.status_code == 400:
            try:
                error = exc.response.json().get("error", {})
            except (ValueError, AttributeError):
                error = {}
            if not isinstance(error, dict):
                error = {}
            if error.get("code") == "json_validate_failed":
                if "max completion tokens reached" in str(error.get("message") or ""):
                    raise GenerationError("groq_output_truncated") from exc
                raise GenerationError("groq_schema_generation_failed") from exc
            raise GenerationError("groq_invalid_request") from exc
        if isinstance(exc, (APIConnectionError, APIStatusError, APITimeoutError)):
            raise GenerationError("groq_provider_unavailable") from exc
        raise


def _content(response):
    try:
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise GenerationError("groq_output_truncated")
        content = choice.message.content
        if not isinstance(content, str):
            raise ValueError("Missing message content")
        return json.loads(content)
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise GenerationError(f"invalid_output: {exc}") from exc


def _usage(response):
    usage = getattr(response, "usage", None)
    return usage.model_dump() if usage is not None else None


def _combined_usage(usages: list[dict | None]) -> dict | None:
    if len(usages) == 1:
        return usages[0]
    totals = {key: sum(item.get(key, 0) for item in usages if isinstance(item, dict))
              for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return {**totals, "by_attempt": usages}


def _reasoning_options(model: str) -> dict:
    if model.startswith("openai/gpt-oss-"):
        return {"reasoning_effort": "low"}
    if model.startswith("qwen/"):
        return {"reasoning_effort": "none"}
    return {}


class GroqGenerator:
    def __init__(self, model: str | None = None, client=None, max_context_chars: int = 8000):
        self.client = client if client is not None else _client()
        self.model = model or os.getenv("GROQ_MODEL") or DEFAULT_MODEL
        self.max_context_chars = max_context_chars

    def generate(self, question: str, supplied: list[dict], manifest: dict) -> dict:
        messages = answer_messages(question, supplied, self.max_context_chars, no_think=False)
        usages = []
        for attempts, output_tokens in ((1, 2048), (2, 4096)):
            try:
                response = _complete(
                    self.client, model=self.model, messages=messages,
                    response_format={"type": "json_schema", "json_schema": {
                        "name": "constitution_answer", "strict": True, "schema": RAW_SCHEMA}},
                    temperature=0.7, top_p=0.8,
                    max_completion_tokens=output_tokens, stream=False,
                    **_reasoning_options(self.model))
                usages.append(_usage(response))
                raw = _content(response)
                return checked_answer(raw, supplied, manifest, self.model,
                                      GROQ_PROMPT_VERSION, _combined_usage(usages), attempts)
            except GenerationError as exc:
                reason = str(exc)
                if attempts == 1 and reason in {"groq_output_truncated", "groq_schema_generation_failed"}:
                    continue
                if attempts == 1 and reason.startswith("invalid_output: Citation quote mismatch"):
                    messages = [*messages, {"role": "user", "content":
                        "La citation précédente ne correspondait pas exactement au texte fourni. Reprends la réponse avec des citations courtes copiées mot pour mot, sans changer les lettres ni la ponctuation. Si aucune citation exacte ne convient, réponds insufficient_evidence avec claims vide."}]
                    continue
                raise
        raise GenerationError("groq_output_truncated")


class GroqDecomposer:
    method = "groq_model"

    def __init__(self, model: str | None = None, client=None):
        self.client = client if client is not None else _client()
        self.model = model or os.getenv("GROQ_MODEL") or DEFAULT_MODEL

    def plan(self, question: str) -> tuple[list[str], dict | None]:
        if not question.strip() or len(question) > 2000:
            raise ValueError("Question length must be between 1 and 2000 characters")
        from .decomposition import PLAN_SCHEMA
        response = _complete(
            self.client, model=self.model,
            messages=[
                {"role": "system", "content": "Tu prépares uniquement la recherche documentaire dans la Constitution marocaine de 2011. Ne réponds pas à la question. N'invente aucun fait. Ne change pas l'intention de l'utilisateur."},
                {"role": "user", "content": f"Question originale : {question}\nPropose une ou deux sous-questions courtes et complémentaires pour trouver les preuves nécessaires. Retourne uniquement l'objet JSON demandé."}],
            response_format={"type": "json_schema", "json_schema": {
                "name": "constitution_search_plan", "strict": True, "schema": PLAN_SCHEMA}},
            temperature=0.7, top_p=0.8,
            max_completion_tokens=768, stream=False, **_reasoning_options(self.model))
        try:
            subquestions = _content(response)["subquestions"]
            if not isinstance(subquestions, list) or not 1 <= len(subquestions) <= 2:
                raise ValueError("Expected one or two subquestions")
            if any(not isinstance(item, str) or not item.strip() or len(item) > 300 for item in subquestions):
                raise ValueError("Invalid subquestion")
            subquestions = [item.strip() for item in subquestions]
            if len({question.casefold(), *(item.casefold() for item in subquestions)}) != len(subquestions) + 1:
                raise ValueError("Duplicate or unchanged subquestion")
            return subquestions, _usage(response)
        except (ValueError, KeyError, TypeError) as exc:
            raise GenerationError(f"invalid_plan: {exc}") from exc
