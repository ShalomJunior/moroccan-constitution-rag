# Constitution Evidence

Recherche documentaire dans la version française de la Constitution marocaine de 2011. L’application retrouve des passages, affiche leur page dans le [PDF institutionnel](https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf) et peut produire une réponse avec des citations vérifiées. Elle ne couvre pas la version arabe.

La version `1.0.4` associe l'application française à une [évaluation finale](reports/final-evaluation.md) de trois systèmes Qwen3-4B sur 90 questions réservées. Les erreurs mesurées sont importantes ; cette version n'est pas une édition juridique officielle ni un outil de conseil juridique. Le mode Groq de l'interface n'est pas le modèle évalué dans cette étude.

## Démarrer

Il faut Python 3.11+, [uv](https://docs.astral.sh/uv/), Poppler, Tesseract et ses données françaises. Le PDF et les fichiers OCR restent sur votre machine ; ils ne sont pas distribués dans le dépôt.

```bash
uv sync --frozen --extra api --extra dense --extra groq
mkdir -p data/raw data/ocr
curl -L --fail -o data/raw/constitution_2011_fr_marocma.pdf https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf
curl -L --fail -o data/ocr/fra.traineddata https://github.com/tesseract-ocr/tessdata_fast/raw/refs/heads/main/fra.traineddata
uv run --frozen constitution-evidence ingest
uv run --frozen constitution-evidence validate-corpus
```

Les empreintes attendues du PDF et des données Tesseract figurent dans le [guide de reproduction](docs/reproduction.md). L’ingestion applique le [journal de corrections OCR](data/annotations/ocr-corrections.jsonl). Si les empreintes des 181 unités reconstruites correspondent à la [revue du corpus](data/annotations/corpus-review.jsonl), `uv run --frozen constitution-evidence certify-corpus` peut rétablir son statut relu. Un changement d’extraction ou de version OCR exige une nouvelle vérification des différences.

Pour lancer l’interface dans Docker :

```bash
docker compose up -d --build
```

Ouvrez [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Le conteneur monte le corpus en lecture seule et garde les modèles de recherche dans un volume Docker. Le premier appel Dense ou Hybride peut télécharger un modèle. Le [guide Docker](docs/container-run.md) détaille les volumes et l’arrêt du service.

Sans Docker : `uv run --frozen --extra api --extra dense --extra groq constitution-evidence serve`.

## Utiliser l’application

- **Extraits** affiche directement les passages retrouvés. BM25, Dense, Hybride et Hybride avec reranking sont disponibles ; BM25 est le choix par défaut.
- **Résumé Groq** utilise une clé `GROQ_API_KEY` placée dans le fichier local `.env` ou dans l’environnement du serveur. La question et les extraits sélectionnés sont envoyés au fournisseur. La clé ne va pas au navigateur.
- **Résumé local** nécessite un [serveur Qwen séparé](docs/local-model.md). L’option est désactivée dans l’interface quand ce serveur est inaccessible ; le conteneur Docker ne le lance pas.
- **Consulter un article** ouvre directement le préambule ou l'un des 180 articles, avec les pages du PDF source.

Les réponses générées contiennent des citations liées à des passages et à des pages du PDF. Le contrôle automatique vérifie l’identité des citations, **pas** que chaque conclusion découle réellement du texte ni que la réponse est complète. Si les passages fournis ne suffisent pas, le système peut s’abstenir. Les essais de développement et les limites observées sont résumés dans le [bilan des réponses](reports/development-answer-review.md).

La section « Passages retrouvés » reste consultable même lorsqu'un résumé s'abstient. Elle distingue les résultats de recherche des passages effectivement inclus dans le contexte de réponse et permet d'ouvrir le texte complet et la page du PDF.

## Vérifier et reproduire

```bash
uv run --frozen --extra api --extra dense --extra groq python -m unittest discover -s tests
uv run --frozen constitution-evidence publication-audit
docker compose config --quiet
```

Le [guide de reproduction](docs/reproduction.md) décrit la source, les commandes et les contrôles. Le [data card](docs/data-card.md) précise la provenance du corpus. Le [rapport d'évaluation finale](reports/final-evaluation.md) présente le test réservé de 90 questions et ses limites. Aucune mesure générale de fiabilité juridique n'est revendiquée pour `1.0.4`.

Le code est sous [licence MIT](LICENSE). Les droits du PDF source et des textes qui en dérivent doivent être examinés séparément avant toute redistribution.
