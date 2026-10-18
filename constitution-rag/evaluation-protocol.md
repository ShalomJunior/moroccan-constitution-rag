# Protocole expérimental et critères de validation

[Accueil](README.md) · [Planning](roadmap.md) · [Spécification](implementation-spec.md)

## 1. Les questions auxquelles le projet doit répondre

1. Quel nettoyage du PDF évite des erreurs de recherche ou de citation ?
2. Un découpage par structure juridique fait-il mieux qu'un découpage fixe en tokens ?
3. Le RAG apporte-t-il un avantage face au texte intégral sur ce corpus ?
4. Le reranking améliore-t-il la sélection des **preuves nécessaires**, pas seulement un score moyen ?
5. La vérification des affirmations diminue-t-elle les réponses incorrectes sans provoquer trop d'abstentions ?
6. Quelles dégradations apparaissent face aux paraphrases et aux fautes de frappe en français ?

Les gains ne sont pas garantis. Une méthode plus simple qui gagne doit rester dans le rapport et peut devenir la version livrée.

## 2. Évaluer l'ingestion avant le RAG

Conserver un échantillon transcrit manuellement depuis les pages du **PDF de référence** : au moins 10 pages, ou toutes si le PDF en contient moins. Inclure pages denses, changements de titre, césures, notes et pages scannées lorsqu'elles existent. La transcription doit être indépendante de l'extraction candidate.

Mesurer :

- Caractères/mots perdus ou substitués, et ordre de lecture incorrect.
- CER, soit distance d'édition en caractères divisée par la longueur de référence ; publier la normalisation utilisée et l'effectif. WER peut compléter mais ne remplace pas l'inspection.
- Exactitude des numéros d'articles, négations et nombres sur cet échantillon.
- Inventaire exhaustif des articles : présence, unicité, ordre, début et fin corrects.
- Proportion de passages reliés à leur page physique et à leur article.

**Critère bloquant :** aucune disparition d'article ou référence cassée connue au moment du gel du corpus. Les cas OCR douteux sont corrigés et consignés ou exclus explicitement du périmètre. Un bon CER moyen ne compense pas une négation perdue.

Pour isoler l'effet du nettoyage, comparer extraction brute et texte nettoyé sur un sous-ensemble dev ciblant les défauts observés. Les annotations restent ancrées dans le PDF et le texte canonique relu. Les copies dégradées artificiellement sont des fixtures expérimentales, jamais des éditions présentées comme authentiques.

## 3. Benchmark de base

### Taille proposée

**180 familles de questions françaises**, réparties avant optimisation en :

- 45 familles de développement : inspection libre et modification des composants.
- 45 familles de validation : sélection des paramètres et de la politique d'abstention.
- 90 familles de test : évaluation finale après gel des configurations.

Une famille regroupe les variantes qui demandent la même information : paraphrases et reformulations adversariales proches. Une famille ne peut pas traverser les splits. Le corpus documentaire, lui, reste accessible dans son intégralité à tous les systèmes : on évalue la généralisation à des questions, pas à des articles jamais indexés.

Répartition indicative à stratifier par type et par thème :

| Type principal | Familles | Comportement attendu |
| --- | ---: | --- |
| Repérage direct ou article explicitement nommé | 60 | Réponse/extrait correctement référencé |
| Reformulation conceptuelle sans reprendre les mots du texte | 40 | Recherche et explication fidèle |
| Plusieurs preuves nécessaires | 30 | Réponse réunissant toutes les conditions utiles |
| Prémisse fausse ou attribution erronée | 20 | Correction sourcée, si le texte permet de trancher |
| Question ambiguë | 10 | Clarification appropriée, sans deviner un fait manquant |
| Question hors du corpus ou indéterminable | 20 | Limite explicitée, pas de règle inventée |
| **Total** | **180** | |

Les sous-groupes sont petits, surtout après split : présenter leurs effectifs et ne pas tirer de conclusions fortes d'un écart d'une ou deux réponses.

### Extensions

- **30 cas de robustesse**, 15 développement et 15 test, répartis en familles d'attaques distinctes. Séparer injection documentaire, instruction utilisateur, citation fabriquée et comportement face à une panne. Les pannes ne sont pas des attaques ni des abstentions correctes.

### Fiche d'annotation

Chaque question possède :

```text
question_id, family_id, split, language, question
category, theme, expected_status, acceptable_statuses
required_claims[]                    # éléments indispensables à une réponse complète
acceptable_evidence_sets[][]         # ensembles alternatifs suffisants de preuves
relevant_articles[], relevant_spans[]
forbidden_inferences[]               # conclusions que le texte ne justifie pas
source_edition, corpus_hash
annotator, review_status, annotation_version
```

Le statut « insuffisant » doit être justifié par la portée du corpus et une recherche attentive ; un échec d'un moteur n'est pas une preuve d'absence. Les questions ambiguës peuvent avoir plusieurs comportements acceptables, explicitement annotés.

### Qualité des labels

- Rédiger des questions naturelles à partir de besoins documentaires ; ne pas faire générer toutes les questions à partir du seul chunk qui sera ensuite recherché.
- Un LLM peut proposer des brouillons sur dev, mais chaque preuve et réponse de référence doit être relue.
- Vérifier les quasi-doublons, y compris traductions et paraphrases.
- Faire relire au moins 20 % des familles par une deuxième personne, ainsi que tous les cas contestés et toutes les traductions évaluées. Noter sa compétence et ses désaccords.
- En l'absence de deuxième personne, effectuer une seconde passe espacée et indiquer clairement « annotation par l'auteur ». Cela ne devient pas une validation indépendante.
- Une validation documentaire par un développeur ne vaut pas expertise juridique. Les interprétations controversées doivent être exclues ou revues par une personne qualifiée.
- Établir les preuves à partir des articles complets et des renvois, pas seulement des résultats du premier moteur. Vérifier un pool des meilleures réponses de plusieurs moteurs pour compléter les jugements ; ne pas supposer automatiquement qu'un passage non jugé est faux.

Pour un projet individuel, connaître les questions que l'on a annotées limite l'indépendance du test. Réserver quand même leurs exécutions et résultats, et demander si possible une petite série externe supplémentaire. Ne pas présenter le test comme une évaluation externe aveugle.

## 4. Configurations de comparaison

| ID | Configuration | But |
| --- | --- | --- |
| B0 | Même LLM sans document | Estimer ce que ses connaissances seules produisent ; pas une version à livrer |
| B1 | Texte intégral propre du PDF de référence | Baseline indispensable si le contexte le permet |
| B2 | BM25 + passages + même LLM | Baseline RAG simple |
| B3 | Dense multilingue + passages + même LLM | Isoler l'apport sémantique |
| B4 | RRF lexical/dense + même LLM | Tester la complémentarité |
| B5 | B4 + reranker | Tester le réordonnancement à candidats fixes |
| B6 | B5 + assemblage structuré / renvois | Tester la couverture des preuves |
| B7 | Meilleure configuration dev + vérification et abstention | Mesurer le risque et le coût de la vérification |
| O1 | Preuves annotées fournies au même LLM | Diagnostic oracle, pas système déployable |

Si le texte intégral dépasse la fenêtre du modèle retenu, le signaler ; ne pas tronquer puis appeler le résultat « texte intégral ». Mesurer aussi une baseline extractive sans génération pour les questions de repérage.

Toutes les configurations partagent la même édition, le même jeu de questions et, sauf expérience dédiée, le même générateur et le même prompt de réponse. Pour B0, la fourniture de citations est naturellement impossible : comparer l'exactitude et les inventions, pas lui attribuer artificiellement un score de citation comparable.

### Ablations à faire sur dev

1. Extraction brute contre nettoyage contrôlé, sur les cas affectés.
2. Fenêtres fixes de 250 puis 500 tokens, overlap de 50, contre paragraphes et articles entiers. Ce sont des points de départ, pas des valeurs optimales connues.
3. Retour du seul passage contre passage avec contexte de son article parent.
4. Sans/avec reranker sur **les mêmes listes candidates sauvegardées**.
5. Sans/avec renvois explicites à budget de contexte comparable ; publier aussi les tokens réels.
6. Sans/avec décomposition bornée pour les seules questions multi-preuves.
7. Génération simple contre vérification structurelle, puis structurelle + sémantique.

Ne pas lancer le produit cartésien de tous les réglages. Utiliser un petit plan séquentiel, conserver les runs négatifs et choisir au plus trois configurations finales : texte intégral, BM25 simple, meilleur pipeline retenu sur validation. Ajouter des variantes finales seulement si le budget et l'annotation le permettent.

## 5. Métriques et dénominateurs

### Recherche

Calculer au niveau **article canonique** pour comparer équitablement les chunkings. Plusieurs passages du même article ne comptent qu'une fois : conserver leur première occurrence, puis recalculer les rangs dans la liste d'articles dédupliquée. Garder en complément des métriques de couverture des spans, plus fines.

- `Recall@k = nombre d'articles pertinents distincts récupérés / nombre d'articles pertinents annotés`.
- `MRR@k = 1 / rang du premier article pertinent` s'il apparaît dans les k premiers, sinon 0.
- `NDCG@k` : gain explicitement défini. Privilégier des jugements binaires pour le premier benchmark ; si l'on utilise plusieurs grades, versionner la convention de gain.
- `complete_evidence@k` : proportion de questions pour lesquelles au moins un ensemble de preuves suffisantes est entièrement couvert. Pour une preuve au niveau span, retrouver l'article sans le paragraphe utile ne suffit pas.
- `context_evidence_coverage` : couverture des preuves dans le **contexte effectivement envoyé** au LLM, après budget et troncature.

Rapporter retrieval sur les questions ayant des preuves annotées ; ne pas assigner Recall=0 aux questions hors corpus sans pertinents. Publier les effectifs exclus. Distinguer rappel du pool candidat, rappel après reranking et couverture du contexte final.

### Citations et réponses

| Mesure | Définition |
| --- | --- |
| Validité des références | Références pointant vers le bon ID/hash et un extrait exact / références produites |
| Précision du support des citations | Couples affirmation–preuve réellement supportés / couples évaluables produits |
| Fidélité des affirmations | Affirmations factuelles supportées par les sources / affirmations factuelles produites |
| Complétude | Éléments requis correctement restitués / éléments requis annotés |
| Succès strict par question | Bonne décision, éléments requis couverts et aucune affirmation substantielle incorrecte/non supportée |
| Décision appropriée | Statut et comportement appartenant aux alternatives acceptables annotées |

Une citation exacte peut être hors sujet. Une réponse correcte de mémoire peut être non fondée sur les passages fournis. Ces deux cas doivent rester distingués.

Définir les unités d'affirmation dans le guide : une phrase contenant trois faits peut nécessiter trois labels. Une preuve conjointe peut utiliser plusieurs spans. Rapporter micro-moyennes par affirmation et macro-moyennes par question, avec leurs effectifs. Zéro citation ou zéro affirmation donne une valeur non applicable pour certaines mesures, pas automatiquement 100 %.

### Abstention et risque

- **Couverture** : proportion de questions recevant une réponse substantielle, complète ou partielle ; publier aussi ces deux catégories séparément.
- **Risque parmi les réponses** : proportion de ces réponses contenant au moins une affirmation substantielle incorrecte ou non supportée selon la grille humaine.
- **Fausse abstention** : proportion de questions annotées répondables auxquelles le système ne fournit aucun élément utile.
- **Réponse indue** : proportion de questions non répondables auxquelles il fournit une conclusion substantielle injustifiée.
- Courbe risque–couverture en variant un seuil sur validation, puis point de fonctionnement figé sur test.

Une réponse partielle peut être fidèle mais incomplète : compter cette distinction, ne pas la masquer dans « succès ». Une panne API entre dans le taux d'échec opérationnel, et non dans la catégorie « bonne abstention ».

Un objectif d'ingénierie possible est un risque observé inférieur à 5 % avec une couverture utile. **Ce n'est ni une promesse ni une certification** : sélectionner une cible avant test, puis publier valeurs, effectifs et intervalles. Avec peu de réponses, même zéro erreur laisse une incertitude importante.

### Coût et latence

- Tokens réels d'entrée/sortie, appels et coût total par question, y compris vérification, retries et décomposition.
- p50/p95 de latence de bout en bout et par étape ; matériel, concurrence et effectif.
- Mesures cache froid/cache chaud séparées. Les valeurs d'un fournisseur API dépendent aussi du réseau et de la charge.
- Taux d'échec, taux de reprise réussie et mémoire maximale mesurée.

## 6. Évaluation humaine et assistée

Un juge automatique sert au tri et à l'analyse à grande échelle, pas à fabriquer seul la vérité terrain.

1. Masquer les noms de systèmes dans les réponses annotées.
2. Évaluer sur les extraits et le PDF source, avec une grille fixée avant les runs finaux.
3. Vérifier humainement les réponses finales des trois systèmes sur les 90 questions test, soit 270 réponses ; prévoir plusieurs journées.
4. Étudier les désaccords du vérificateur automatique sur un échantillon stratifié, avec ses faux positifs et faux négatifs.
5. Si l'échantillon du juge est enrichi en erreurs, ne pas annoncer sa précision sur cet échantillon comme sa précision en usage normal sans correction d'échantillonnage.

Calculer des intervalles bootstrap appariés pour les différences de score entre systèmes, en rééchantillonnant les **familles de questions**. Les traductions ne constituent pas des tirages indépendants. Fixer la seed et documenter le nombre de réplications, par exemple 2 000. Pour les petits sous-groupes, publier les comptes bruts et éviter les classements trop affirmatifs.

Sur une petite sélection dev, répéter la génération trois fois pour estimer sa variabilité. Température zéro ne garantit pas une reproduction bit à bit d'une API. La campagne finale à une génération par question doit l'indiquer explicitement.

## 7. Prévenir les fuites et les comparaisons trompeuses

- Ne pas choisir chunking, prompts, modèles, seuils ou checkpoint sur les scores du test.
- Les reformulations d'une même question restent dans un seul split.
- Les prompts few-shot utilisent uniquement des exemples dev autorisés.
- Un oracle ne transmet jamais des annotations au pipeline de production.
- Un changement de qrels après inspection du test exige un erratum versionné ; il ne doit pas discrètement améliorer une seule méthode.
- Les expériences ajoutées après publication utilisent un nouveau test ou sont étiquetées exploratoires sur l'ancien test.
- Une mise à jour du corpus ou du protocole crée une nouvelle version des résultats, associée à son code et à ses données.

## 8. Manifeste de chaque run

Conserver : commit et état du working tree, config complète, environnement verrouillé, hashes PDF/corpus/annotations/index, modèles et révisions, prompts exacts, paramètres de génération, seed lorsque disponible, matériel, horodatage, split, IDs des questions, résultats individuels, erreurs, coûts et latences.

Les vérifications doivent permettre de relier : **cellule du tableau → run → réponse brute → contexte envoyé → passages → pages du PDF de référence**.

## 9. Publication et règles d'arrêt

On peut publier une version réussie du projet même si B1 gagne contre B7. La valeur réside dans la comparaison et la qualité de l'outil livré.

Ne pas déclarer le projet évalué si le corpus n'est pas contrôlé, si les références ne sont pas résolubles ou si le test a servi à choisir les paramètres. Ne pas déclarer le système exempt d'hallucinations sur la base de quelques exemples.


Livrables scientifiques minimaux : corpus documenté, benchmark versionné, guide d'annotation, trois systèmes finaux comparés, sorties sauvegardées, tableau recalculable, analyse d'erreurs et limites explicites.
