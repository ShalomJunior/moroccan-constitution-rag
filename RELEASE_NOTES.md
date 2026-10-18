# Version 0.1.0 — application française

Cette version permet de rechercher dans le texte français de la Constitution marocaine de 2011 et d'ouvrir, pour chaque citation, la page correspondante du PDF institutionnel.

## Inclus

- Ingestion OCR reproductible, corrections ancrées au PDF et contrôle de l'inventaire des 180 articles et du préambule.
- Recherche BM25, Dense, Hybride et Hybride avec reranking ; consultation des extraits dans une interface web.
- Réponses facultatives via Groq ou un serveur Qwen séparé, avec vérification des identifiants, empreintes, positions et textes cités.
- API, image Docker CPU, dépendances verrouillées et tests hors ligne.

## Limites connues

Les contrôles de citation ne prouvent ni la justesse juridique ni la complétude d'une réponse. Sur 15 questions de développement relues après les dernières modifications de génération, 8 réponses satisfaisaient les quatre critères de la grille. Ce petit échantillon ne mesure pas la fiabilité générale. Le benchmark final et le test réservé ne sont pas terminés ; cette version n'est donc pas la release évaluée `v1.0`.

Le PDF source, les modèles, le corpus généré, les clés et les runs ne sont pas inclus. Le [README](README.md) donne les commandes pour reconstruire le corpus localement et lancer l'application. Les conditions de redistribution du PDF et des textes dérivés doivent être vérifiées séparément.

Corpus local utilisé pour les vérifications de cette version : empreinte des articles `c319ecb4cabe0eaafc3de18779cc210ec8fa83cffbaeb2259393073e9fb4901c` ; empreinte des passages `a4abf1b043a72c18d6dcc740f3f3ebbbc1a29aeebf0eedb8c1264d0793c5079c`.

## Vérification de la release

Un clone temporaire de la branche `release/0.1.0` a installé les dépendances verrouillées et passé 59 tests. Avec le PDF et les données Tesseract attendus, il a reconstruit les 181 unités et 483 passages aux empreintes ci-dessus, puis `validate-corpus`, `certify-corpus` et une question en mode extraits ont réussi. L'audit des fichiers suivis n'a trouvé ni clé ni fichier local exclu.
