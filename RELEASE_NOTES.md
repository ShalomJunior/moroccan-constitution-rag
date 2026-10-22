# Version 1.0.1 — revue finale corrigée

La revue finale d'un second relecteur remplace les jugements précédents. Sur 205 réponses sans erreur technique, 147 sont acceptables, dont 126 sans réserve et 21 avec réserves mineures. Les 65 erreurs techniques restent des échecs. Sur les 90 questions du test réservé, BM25 obtient 51 succès sans réserve et 56 réponses acceptables ; l'hybride 50 et 57 ; le texte intégral 25 et 34. Les intervalles appariés ne démontrent pas de gain de l'hybride face à BM25. Le [rapport](reports/final-evaluation.md) expose les catégories, le calcul et les limites.

Le script personnel de présentation n'est plus suivi par Git et l'audit de publication bloque son ajout futur. La version 1.0.0 et son historique restent accessibles ; la présente version corrige le rapport actif sans réécrire l'historique.

## Historique

# Version 1.0.0 — application française évaluée

Cette version conserve la recherche documentaire et l'interface française, et publie les résultats agrégés du test réservé Qwen3-4B. Le corpus, les questions et les trois configurations ont été gelés au commit `726abe0632f027dd430e4bac405ca0b66513b8c6` avant l'exécution. La revue aveugle des réponses a été fournie par la personne responsable du projet ; le rapport expose la divergence entre le résumé de cette revue et ses lignes détaillées.

Sur 90 questions, BM25 RAG et le pipeline hybride sélectionné sur validation obtiennent chacun 51 succès stricts ; le texte intégral en obtient 25. Les erreurs techniques sont respectivement 11, 19 et 35. Le [rapport](reports/final-evaluation.md) détaille les intervalles appariés, les échecs et les limites. Le résultat ne démontre pas de gain de l'hybride sur BM25. Ces chiffres concernent les systèmes Qwen figés, pas le mode Groq de l'interface, et ne certifient pas un usage juridique autonome.

Le PDF, le corpus généré, les questions et réponses du test, les jugements, les clés et les poids du modèle restent hors du dépôt. L'acquisition du PDF institutionnel et la reconstruction locale sont décrites dans le [guide](docs/reproduction.md). Le code de la version passe les tests hors ligne, l'audit de publication et la configuration Docker ; CI réinstalle depuis un clone propre. La révision d'évaluation reste distincte des modifications de rapport et de versionnage qui ont suivi le test.

## Historique : version 0.1.0 — application française

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
