"""Readable source packet for author review of provisional benchmark questions."""
from pathlib import Path

from .store import read_jsonl


def write_question_packet(questions_path: Path, articles_path: Path, passages_path: Path,
                          source_url: str, output_path: Path, split: str = "dev") -> dict:
    if split not in {"dev", "validation", "test"}:
        raise ValueError("Unknown benchmark split")
    questions = [q for q in read_jsonl(questions_path) if q.get("split") == split]
    if not questions:
        raise ValueError(f"No {split} questions")
    articles = {row["article_number"]: row for row in read_jsonl(articles_path)}
    passages = {}
    for passage in read_jsonl(passages_path):
        passages.setdefault(passage["article_number"], []).append(passage)
    lines = [f"# Revue des questions — {split}", "",
             "Brouillon de travail. Les articles ci-dessous sont des pistes, pas des preuves validées.",
             "Vérifier le PDF et le texte canonique avant d'inscrire les spans exacts et `review_status: reviewed` dans `questions.jsonl`.", ""]
    for q in questions:
        qid = q["question_id"]
        lines += [f"## {qid} — {q['question']}", "",
                  f"Statut : `{q.get('review_status', 'missing')}` · catégorie proposée : `{q.get('category', 'à définir')}`", "",
                  "À renseigner : `expected_status`, `acceptable_statuses`, `required_claims`, `relevant_articles`, `relevant_spans`, `acceptable_evidence_sets`, `forbidden_inferences`, `annotator`, `annotation_version`.", ""]
        candidates = q.get("candidate_articles", [])
        if not candidates:
            lines += ["Aucun article candidat. Documenter la recherche avant de conclure que la réponse est absente.", ""]
        for number in candidates:
            article = articles.get(number)
            if article is None:
                raise ValueError(f"{qid}: candidate article {number} is absent")
            pages = ", ".join(f"[p. {page}]({source_url}#page={page})" for page in article.get("page_spans", []))
            lines += [f"### Article {number} · {pages}", "", "Texte canonique :", ""]
            lines += [f"> {line}" if line else ">" for line in article["canonical_text"].splitlines()]
            lines += ["", "Passages à examiner (offsets propres à chaque passage) :", ""]
            for passage in passages.get(number, []):
                lines += [f"- `{passage['passage_id']}` — {len(passage['canonical_text'])} caractères; PDF p. {', '.join(map(str, passage.get('page_spans', [])))}"]
                lines += ["", "```text", passage["canonical_text"], "```", ""]
            lines.append("")
        lines += ["Décision de revue : ☐ accepter ☐ corriger ☐ retirer · Notes :", "", "---", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return {"questions": len(questions), "split": split, "output": str(output_path)}
