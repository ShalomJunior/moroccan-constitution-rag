# Évaluation sur Kaggle

Le test final français compare le texte intégral, BM25 RAG et le pipeline hybride avec Qwen3-4B quantifié en NF4, via Hugging Face Transformers et bitsandbytes. Les paramètres et les résultats figurent dans le [rapport final](../reports/final-evaluation.md). Le corpus traité et les annotations complètes sont des entrées privées ; le dépôt contient les scripts et les notebooks nécessaires à l'exécution.

## Préparer les entrées

La construction d'un bundle exige le corpus traité, les 180 questions annotées, les résultats de validation et le manifeste de gel sous `runs/`. Elle vérifie leurs empreintes et exige un checkout propre au commit enregistré dans le manifeste. Le commit évalué est `726abe0632f027dd430e4bac405ca0b66513b8c6` ; un checkout de la dernière version ne remplace pas cette révision pour reproduire le test figé.

Dans l'environnement correspondant au manifeste :

```bash
uv run --frozen python scripts/build_kaggle_final_bundle.py
```

Le bundle est écrit dans `runs/constitution-evidence-final-input.zip`. Il contient les données réservées et doit rester dans un dataset Kaggle privé. Pour reprendre une exécution interrompue, le constructeur accepte `--previous-results runs/constitution-final-results.zip` et vérifie la compatibilité des résultats précédents.

## Exécuter

1. Sélectionner **GPU T4 x2**, activer Internet et ajouter le dataset privé contenant le bundle.
2. Ouvrir `notebooks/kaggle_final.ipynb`. La première cellule accepte le ZIP ou le dossier extrait automatiquement par Kaggle.
3. Utiliser **Save Version → Save & Run All** pour exécuter sans garder le navigateur ouvert.
4. Télécharger `constitution-final-results.zip` depuis les sorties de la version sauvegardée.

Le modèle utilise la révision `1cfa9a7208912126459214e8b04321603b3df60c`. L'exécution est isolée dans un processus PyTorch, avec JAX sur CPU, quantification NF4, capacité YaRN de 65 536 tokens et préremplissage par blocs de 512 tokens. Chaque réponse est enregistrée immédiatement. Les fichiers `fulltext/answers.jsonl`, `bm25_rag/answers.jsonl` et `selected_pipeline/answers.jsonl`, sous `runs/final-reserved-qwen4b-transformers/`, permettent de suivre l'avancement dans une session interactive. Le test complet exige 90 lignes par système, y compris les erreurs enregistrées.

Kaggle applique une limite de durée aux versions sauvegardées. Un arrêt forcé peut empêcher la création du ZIP final ; les lignes déjà écrites sont les points de reprise disponibles dans les sorties conservées. Les bundles, sorties individuelles et notebooks exécutés contenant les questions réservées restent privés.
