# Présentation de cinq minutes

Cette trame accompagne une démonstration locale. Elle décrit les résultats du test réservé sans ouvrir les questions ni les réponses privées.

## 0:00–0:45 — Problème et source

Présenter le PDF institutionnel français de la Constitution marocaine de 2011. Montrer qu'une recherche documentaire doit pouvoir revenir à l'article et à la page d'origine. Préciser que l'application ne couvre ni l'arabe ni les changements ultérieurs du droit, et qu'elle ne fournit pas de conseil juridique.

## 0:45–1:45 — Du PDF aux passages

Montrer `data/annotations/ocr-corrections.jsonl` et le schéma du corpus dans le [data card](data-card.md). Expliquer la lecture des pages, l'OCR français, la séparation du préambule et des 180 articles, puis les passages avec identifiants, empreintes, bornes et pages. Le PDF et le corpus reconstruit sont locaux ; le dépôt conserve les commandes, la provenance et les empreintes. La revue du corpus a été faite par une seule personne.

## 1:45–2:45 — Démonstration de l'application

Lancer `docker compose up -d --build`, ouvrir `http://127.0.0.1:8000/`, puis poser une question sur l'article 20 en mode **Extraits** avec BM25. Ouvrir un passage et sa page PDF. Montrer ensuite les choix Dense et Hybride, sans les présenter comme intrinsèquement meilleurs. Si une clé Groq est disponible, une génération peut être montrée séparément ; préciser qu'elle transmet la question et les extraits au fournisseur et qu'elle n'est pas couverte par le test Qwen final.

## 2:45–3:45 — Évaluation gelée

Afficher le [tableau du rapport final](../reports/final-evaluation.md). Décrire les 45 familles de développement, 45 de validation et 90 de test réservé, puis le gel du corpus, du modèle et des configurations avant le test. Les trois systèmes Qwen3-4B ont été jugés en aveugle sur les quatre critères : décision, fidélité, complétude et citations. BM25 RAG et l'hybride ont chacun 51 succès stricts sur 90 ; le texte intégral en a 25. Les 65 sorties en erreur technique ont été comptées comme échecs.

## 3:45–5:00 — Ce que montrent les échecs

Expliquer trois exemples sans révéler les questions réservées : une citation modifiée est rejetée automatiquement ; une abstention peut être erronée lorsque la disposition existe ; une citation exacte peut accompagner une conclusion qui inverse le sens du texte. L'hybride ne montre pas de gain strict sur BM25 dans ce test. Conclure en ouvrant la section « Limites » du rapport : un seul relecteur, une seule édition française, aucune garantie de fiabilité juridique générale. Montrer les commandes de reproduction et l'audit de publication plutôt que de prétendre que le score suffit à certifier le produit.
