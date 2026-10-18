"""Resolve short article follow-ups without trusting earlier answer text."""
import re
from .retrieval import explicit_article_numbers

FOLLOWUP = re.compile(r"\b(?:cet article|ce même article|l'article précédent)\b", re.IGNORECASE)


def resolve(question: str, history: list[dict]) -> dict:
    explicit = explicit_article_numbers(question)
    if explicit or not FOLLOWUP.search(question):
        return {"resolved_question": question, "used_article": None, "needs_clarification": False}
    articles = list(dict.fromkeys(history[-1].get("article_numbers", []))) if history else []
    if len(articles) != 1:
        return {"resolved_question": None, "used_article": None, "needs_clarification": True}
    article = articles[0]
    return {"resolved_question": FOLLOWUP.sub(f"l'article {article}", question),
            "used_article": article, "needs_clarification": False}


def next_articles(question: str, sources: list[dict]) -> list[int]:
    explicit = explicit_article_numbers(question)
    if len(explicit) == 1:
        return explicit
    if len(explicit) > 1:
        return explicit[:5]
    return list(dict.fromkeys(source["article_number"] for source in sources
                              if source.get("article_number") is not None))[:5]
