# Constitution Evidence

Recherche documentaire dans la version française de la Constitution marocaine de 2011. L’application retrouve des passages, affiche leur page dans le [PDF institutionnel](https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf) et peut produire une réponse avec des citations vérifiées. Elle ne couvre pas la version arabe.

La version `0.1.0` est une **version applicative**. Elle permet de consulter le corpus et de tester les différents modes de recherche. Elle ne constitue ni une édition juridique officielle ni un système dont la fiabilité a été établie par une évaluation finale.

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

Les réponses générées contiennent des citations liées à des passages et à des pages du PDF. Le contrôle automatique vérifie l’identité des citations, **pas** que chaque conclusion découle réellement du texte ni que la réponse est complète. Si les passages fournis ne suffisent pas, le système peut s’abstenir. Les essais de développement et les limites observées sont résumés dans le [bilan des réponses](reports/development-answer-review.md).

La section « Passages retrouvés » reste consultable même lorsqu'un résumé s'abstient. Elle distingue les résultats de recherche des passages effectivement inclus dans le contexte de réponse et permet d'ouvrir le texte complet et la page du PDF.

## Vérifier et reproduire

```bash
uv run --frozen --extra api --extra dense --extra groq python -m unittest discover -s tests
uv run --frozen constitution-evidence publication-audit
docker compose config --quiet
```

Le [guide de reproduction](docs/reproduction.md) décrit la source, les commandes et les contrôles. Le [data card](docs/data-card.md) précise la provenance du corpus. Les résultats des petites séries de développement ne remplacent pas une évaluation indépendante : le benchmark de 45 questions de développement, 45 de validation et 90 de test réservé n’est pas terminé. Aucune mesure générale de fiabilité juridique n’est revendiquée pour `0.1.0`.

Le code est sous [licence MIT](LICENSE). Les droits du PDF source et des textes qui en dérivent doivent être examinés séparément avant toute redistribution.
