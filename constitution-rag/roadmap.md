# Feuille de route quotidienne : du PDF officiel à un RAG évalué

[Accueil](README.md) · [Spécification](implementation-spec.md) · [Protocole d'évaluation](evaluation-protocol.md) · [Sources PDF](sources.md)

## Organisation

**40 journées pour le socle, puis 10 journées optionnelles.** Une journée représente environ 5 à 6 heures de travail concentré. À raison de 5 journées par semaine, le socle prend environ 8 semaines ; conserver les week-ends comme marge ou repos. Les délais d'annotation et de relecture peuvent prolonger ce calendrier.

Chaque journée :

- 30 à 45 minutes de lecture ciblée ou d'analyse des erreurs.
- 3 à 4 heures de réalisation, incluant l'annotation quand elle est prévue.
- 45 à 60 minutes de vérification et de mesure.
- 15 minutes dans `PROJECT_LOG.md` : changement, résultat, échec, prochaine décision.

Les chemins de fichiers à produire décrivent les livrables du futur dépôt. Chaque journée définit un travail, une preuve de réalisation et un contrôle de qualité.

### Vue d’ensemble

| Période | Résultat attendu |
| --- | --- |
| J1–J5 | PDF extrait, nettoyé, structuré et contrôlé |
| J6–J10 | Benchmark conçu, BM25 et baseline texte intégral opérationnels |
| J11–J15 | Chunking et retrieval comparés, configuration candidate sélectionnée |
| J16–J20 | Réponses structurées, citations vérifiables et abstention |
| J21–J25 | Preuves multiples, revue du français et clarification |
| J26–J30 | API, interface, reprise des runs, tests et corpus annoté figé |
| J31–J35 | Ablations, sélection sur validation et configuration finale figée |
| J36–J40 | Test réservé, évaluation humaine, rapport et release reproductible |
| J41–J50 | Une extension de recherche choisie à partir des résultats |

### Périmètre retenu

- Entrée : PDF institutionnel de la Constitution de 2011, selon le choix documenté dans [Sources PDF](sources.md).
- Périmètre **français uniquement**. Les travaux arabes et interlangues sont retirés.
- Gemini Flash via un adaptateur indépendant du fournisseur ; version choisie et enregistrée au lancement.
- Socle sur la Constitution seule ; autres lois et jurisprudence restent hors périmètre initial.
- Chaque expérience possède sa configuration, ses sources et ses résultats individuels sauvegardés.

## Semaine 1 : rendre le PDF exploitable et vérifiable

### J1 : fixer la source et définir le produit

- **Construire :** télécharger le PDF institutionnel retenu, contrôler son édition et sa langue, calculer son hash. Créer le dépôt, l'environnement isolé et la configuration. Définir les besoins utilisateurs, langues, budget et limites documentaires.
- **Livrable :** `docs/project-scope.md`, manifeste source et fiche d'une page sur le périmètre.
- **Vérifier :** URL institutionnelle, fichier PDF lisible, version du texte distincte de la date de téléchargement ; objectifs évaluables et corpus clairement délimité.

### J2 : diagnostiquer la mise en page et comparer deux extractions

- **Construire :** extraire page par page avec deux outils, par exemple Poppler et un extracteur conservant les coordonnées. Identifier couverture, sommaire, corps, colonnes, pieds de page et éventuelles annexes. Inspecter au moins 10 pages représentatives ou toutes si le fichier est plus court.
- **Livrable :** `reports/pdf-diagnostics.md`, textes par page et échantillon transcrit manuellement.
- **Vérifier :** le texte principal ne se mélange pas avec les éléments éditoriaux. Choisir extraction native, OCR ou traitement mixte selon le diagnostic réel du fichier.

### J3 : nettoyage avec conservation de la provenance

- **Construire :** séparer les zones par mise en page ; retirer en-têtes/pieds répétitifs du texte d'indexation, isoler sommaire et annexes, réparer espaces et césures. Préserver les listes, notes utiles et conditions présentes dans le corps du texte.
- **Livrable :** `clean_pages.jsonl`, règles de nettoyage, différences avant/après et tests ciblés.
- **Vérifier :** nombres, négations et ordre de lecture conservés sur l'échantillon. Mesurer les erreurs de transcription et traiter les erreurs qui changent le sens.

### J4 : reconstruire articles, titres et préambule

- **Construire :** parseur tenant compte des positions/titres, et non de chaque occurrence textuelle de « Article ». Normaliser les formes comme « Article premier » dans les métadonnées. Conserver les renvois à d'autres articles dans le contenu de l'article courant.
- **Livrable :** `articles.jsonl` avec 180 articles attendus plus le préambule, liens pages et journal de parsing.
- **Vérifier :** 180 numéros uniques de 1 à 180 pour l'édition 2011, préambule complet et fin correcte du dernier article. Vérifier aussi les frontières : le bon nombre d'articles ne suffit pas.

### J5 : premières variantes de chunking et gel du corpus

- **Construire :** trois découpeurs : article entier, paragraphes avec lien au parent, fenêtres en tokens avec overlap. Produire des IDs stables, offsets et hashes. Mesurer tailles médiane/maximale et passages dépassant la limite des encodeurs.
- **Livrable :** corpus `v1`, rapport de qualité et statistiques des chunks.
- **Vérifier :** chaque extrait remonte au PDF ; toutes les unités sont présentes ; aucune annexe éditoriale n'est fusionnée avec le dernier article. Rejouer l'ingestion donne le même résultat logique.

**Jalon 1 :** ne pas comparer les moteurs tant que le préambule, les frontières d'articles et la provenance sont incorrects.

## Semaine 2 : benchmark et premières références

### J6 : écrire le contrat d'évaluation

- **Construire :** guide d'annotation, catégories de questions, définition des preuves suffisantes, distinction réponse/abstention/clarification/erreur technique. Écrire 15 questions de calibration hors benchmark final.
- **Livrable :** `annotation-guide.md`, schémas des questions et jugements.
- **Vérifier :** savoir distinguer citation exacte mais inutile, réponse fidèle mais incomplète et réponse correcte non sourcée. Corriger le guide sur ces exemples.

### J7 : constituer les familles et réserver les splits

- **Construire :** rédiger l'inventaire de 180 familles de questions françaises ; répartir 45 dev, 45 validation et 90 test par famille, catégorie et thème. Les formulations peuvent être affinées pendant l'annotation avant gel. Réserver un registre des paraphrases/traductions.
- **Livrable :** `questions.jsonl`, `splits.json`, rapport de doublons et plan d'annotation.
- **Vérifier :** aucune famille dans deux splits. Les questions test ne servent plus à choisir les prompts ou les composants. Documenter que l'auteur connaît les questions qu'il a rédigées.

### J8 : annoter et implémenter BM25

- **Construire :** annoter une première série dev avec articles et spans ; BM25 sur corpus contrôlé et lookup d'article explicite. Commencer la relecture des références.
- **Livrable :** premier run retrieval, scores par question et tests de cutoff.
- **Vérifier :** rang 11 exclu de MRR@10, article retrouvé via plusieurs chunks compté une fois, article inexistant traité explicitement. Continuer l'annotation par lots au cours des jours suivants.

### J9 : baseline générative avec texte intégral

- **Construire :** adaptateur fournisseur, configuration du modèle, comptage des tokens et budget d'appels. Lancer sur 10 à 15 questions dev : sans document, texte intégral nettoyé, BM25 + contexte. Utiliser les mêmes instructions de réponse et le même modèle quand applicable.
- **Livrable :** réponses brutes, contextes, coûts et latences du pilote.
- **Vérifier :** toute la Constitution tient effectivement dans le budget retenu pour la baseline intégrale ; sinon consigner cette limite. Une réponse fluide n'est pas encore un succès évalué.

### J10 : premier bilan et préparation des annotations complètes

- **Construire :** terminer les 45 annotations dev, relire les erreurs du pilote et vérifier le budget prévisionnel. Faire une session de calibration avec le deuxième relecteur si disponible.
- **Livrable :** premier tableau dev et plan pour terminer validation/test avant J30.
- **Vérifier :** les calculs proviennent des artefacts ; les limites de la baseline sont nommées. Si l'annotation prend davantage de temps, prolonger cette phase plutôt que réduire la qualité des labels.

**Jalon 2 :** disposer d'un moteur lexical, d'une baseline texte intégral, de questions annotées et d'un budget mesuré.

## Semaine 3 : retrieval et expérience contrôlée sur le chunking

Réserver environ 1 à 2 heures par jour à l'annotation validation/test pendant cette semaine et la suivante. Cette activité ne permet pas de consulter les sorties du test ou d'ajuster les systèmes sur elles.

### J11 : recherche dense et troncature

- **Construire :** embeddings, recherche exacte et persistance avec manifeste modèle/corpus. Commencer avec un encodeur multilingue, testé d'abord sur FR→FR.
- **Livrable :** baseline dense, tailles des entrées et taux de troncature par chunking.
- **Vérifier :** normalisation et métrique de similarité cohérentes, encodeur requêtes/documents identique à l'index sauvegardé, aucun article long tronqué sans mesure.

### J12 : comparer les chunkings

- **Construire :** comparer article entier, paragraphes et fenêtres 250/500 tokens sur dev ; garder modèle, questions et règles d'évaluation fixes. Rapporter résultats au niveau article et couverture des spans.
- **Livrable :** tableau qualité/tokens/latence, avec cinq exemples de frontières problématiques.
- **Vérifier :** l'overlap n'augmente pas artificiellement le rappel par duplication ; les IDs de référence restent les mêmes malgré le changement de segmentation.

### J13 : fusion hybride

- **Construire :** RRF avec profondeurs lexicales/denses indépendantes de la sortie ; tester un petit nombre de valeurs préannoncées sur dev.
- **Livrable :** BM25 vs dense vs hybride, listes candidates conservées.
- **Vérifier :** mêmes corpus et questions, ordre déterministe à scores égaux ; expliquer les cas où la fusion dégrade les résultats.

### J14 : reranking et coût

- **Construire :** intégrer un cross-encoder et comparer reranking de préfixes de listes candidates figées, par exemple 10/20/40 si leur taille le permet.
- **Livrable :** qualité, couverture des preuves, latence et mémoire par profondeur.
- **Vérifier :** seule la profondeur rerankée change ; ne pas modifier simultanément la recherche initiale. Les limites de longueur du reranker sont mesurées.

### J15 : sélectionner une configuration retrieval

- **Construire :** analyser les échecs dev : vocabulaire, mauvaise frontière, preuve manquante, confusion entre articles, translation. Choisir une configuration candidate et une baseline simple.
- **Livrable :** `reports/retrieval-study.md`, configurations et commandes de reproduction.
- **Vérifier :** chaque composant conservé a une justification mesurée. Si BM25 ou le dense seul gagne, le garder comme candidat principal.

**Jalon 3 :** le retrieval est comparable et sa profondeur est définie ; la génération ne sert pas à masquer un corpus incorrect.

## Semaine 4 : réponses avec preuves vérifiables

### J16 : assembler le contexte

- **Construire :** budget de tokens, déduplication, contexte parent et ordre des passages. Conserver le contexte réellement envoyé, pas seulement la liste des hits.
- **Livrable :** `EvidencePack`, traces et tests de dépassement de budget.
- **Vérifier :** réserver les tokens de sortie ; une exception juridique située juste après le passage récupéré n'est pas supprimée sans que ce risque soit observable.

### J17 : réponse structurée au niveau des affirmations

- **Construire :** schéma `Answer`/`Claim`/`EvidenceSpan`, statuts de réponse et prompt versionné. Limiter la réponse à des affirmations accompagnées de références locales.
- **Livrable :** génération structurée sur dev et fixtures de réponses invalides.
- **Vérifier :** le parseur refuse les statuts inconnus et les IDs non fournis. Le modèle n'a pas la responsabilité de construire seul l'URL officielle ou le numéro de page.

### J18 : contrôles déterministes des citations

- **Construire :** validation ID/hash/offset/extrait, références vers le PDF original, réparation bornée des erreurs de format.
- **Livrable :** tests adversariaux de citations inventées, copiées du mauvais article ou issues d'un ancien corpus.
- **Vérifier :** un extrait faux est rejeté ; un extrait exact mais hors sujet reste identifié comme un problème sémantique non résolu par ce validateur.

### J19 : grille humaine et vérificateur sémantique

- **Construire :** annoter des couples affirmation/preuves du dev, puis comparer un vérificateur LLM ou NLI à ces jugements. Inclure contradictions, omissions, exceptions et preuves conjointes.
- **Livrable :** matrice de confusion du vérificateur et exemples de faux accords.
- **Vérifier :** ne pas appeler « vérité terrain » les propres réponses du vérificateur ; garder un verdict incertain et les désaccords humains.

### J20 : abstention et réponse partielle

- **Construire :** politique simple combinant signaux de retrieval et contrôles ; au plus une réparation avant abstention/partiel. Préparer la courbe risque–couverture sur dev, puis réserver le choix final du seuil à validation.
- **Livrable :** comparaison réponse systématique / seuil simple / vérification, avec coûts.
- **Vérifier :** une panne API n'est pas une bonne abstention ; zéro réponse n'est pas une stratégie utile même si elle ne contient aucune erreur factuelle.

**Jalon 4 :** une réponse peut être suivie jusqu'à ses preuves ; les compteurs de citations sont distincts de la fidélité et de la complétude.

## Semaine 5 : questions complexes et langues

### J21 : renvois explicites entre articles

- **Construire :** extraire les renvois, vérifier leurs cibles et créer un graphe léger. Ajouter une expansion d'au plus un saut sous budget.
- **Livrable :** arêtes avec provenance et expérience sans/avec expansion.
- **Vérifier :** un renvoi ne devient pas une nouvelle frontière d'article. Une relation déduite par LLM reste distinguée d'un renvoi écrit.

### J22 : décomposition bornée des questions multi-preuves

- **Construire :** variante qui produit au plus trois sous-questions, récupère leurs preuves puis assemble une réponse. Pas de boucle autonome illimitée.
- **Livrable :** comparaison avec recherche unique sur la catégorie multi-preuves.
- **Vérifier :** la décomposition ne change pas l'intention, n'invente pas de faits et ne dépasse pas le plafond d'appels. Mesurer les preuves manquantes et le coût supplémentaire.

### J23 : revue approfondie du corpus français

- **Construire :** relire les 180 articles et le préambule contre les pages du PDF, corriger les erreurs OCR et consigner chaque correction.
- **Livrable :** corpus français relu avec journal de corrections et nouveaux hashes.
- **Vérifier :** chaque correction correspond au PDF et les offsets, hashes et pages du corpus corrigé restent cohérents.

### J24 : robustesse de la recherche française

- **Construire :** comparer questions directes, paraphrases et fautes de frappe sur les familles françaises de développement ; analyser les échecs de recherche lexicale, dense et hybride.
- **Livrable :** étude des formulations françaises avec erreurs par famille et niveau de relecture.
- **Vérifier :** les paraphrases restent dans le split de leur famille et chaque citation renvoie à la version française effectivement utilisée.

### J25 : clarification et dialogue court

- **Construire :** gérer une clarification puis une reformulation autonome de la question ; historique borné. Prévoir changement de sujet et références comme « cet article ».
- **Livrable :** 15 dialogues dev avec états attendus et tests d'isolation de sessions.
- **Vérifier :** chaque nouvelle réponse récupère ses preuves ; une ancienne réponse du chatbot n'est jamais traitée comme source constitutionnelle. Si le dialogue n'est pas évalué au test, l'indiquer comme fonctionnalité expérimentale.

**Jalon 5 :** les capacités complexes ont des tests séparés ; le nombre d'étapes du pipeline n'est pas pris pour une amélioration automatique.

## Semaine 6 : application utilisable et exécution fiable

### J26 : API typée

- **Construire :** routes `/ask`, `/sources/{id}`, `/health`, `/version` avec schémas, erreurs définies et limites d'entrée. Séparer l'orchestration du code de l'interface.
- **Livrable :** API et tests d'intégration hors ligne avec fournisseur simulé.
- **Vérifier :** réponses déterministes des fixtures, absence de mélange entre utilisateurs, cas de source introuvable et budget invalide.

### J27 : interface avec lecture des preuves

- **Construire :** écran question/réponse, citations ouvrant le passage exact, article et page du PDF français.
- **Livrable :** démo navigable et trois parcours enregistrés.
- **Vérifier :** un utilisateur peut contrôler une affirmation en deux actions ; les extraits ne sont pas masqués derrière des IDs techniques incompréhensibles.

### J28 : reprise, cache et observabilité

- **Construire :** sauvegarde après chaque question, reprise idempotente, retries bornés, cache versionné, logs structurés sans secrets, compteurs d'appels/tokens/latence.
- **Livrable :** campagne volontairement interrompue puis reprise et rapport des coûts.
- **Vérifier :** aucune réponse perdue ou comptée deux fois ; changer prompt/corpus/modèle invalide le cache approprié ; retries inclus dans le coût.

### J29 : robustesse et sécurité de la démo

- **Construire :** cas d'injection documentaire, citations forgées, entrées longues, source absente, contenu HTML et panne fournisseur. Mettre les clés hors dépôt et borner appels/concurrence.
- **Livrable :** modèle de menace court, suite de cas et corrections associées.
- **Vérifier :** aucune instruction issue du document n'exécute une action ; aucune clé n'arrive au navigateur. Tester sans lancer d'attaque contre un service tiers.

### J30 : installation propre, tests utilisateurs et gel des annotations

- **Construire :** environnement verrouillé, CI hors ligne, commande de lancement ; faire exécuter cinq tâches à deux ou trois utilisateurs volontaires si disponibles. Terminer relecture et gel des 180 familles et des variantes linguistiques retenues.
- **Livrable :** rapport d'installation, problèmes d'utilisabilité et benchmark `v1` avec hashes.
- **Vérifier :** installation sans chemins personnels, pas de `pip install` lancé silencieusement par le programme ; toutes les questions finales ont un statut de relecture explicite. Sans utilisateurs externes, nommer les essais « walkthrough par l'auteur ».

**Jalon 6 :** l'application fonctionne depuis un environnement propre ; les sources, annotations et configurations sont versionnées.

## Semaine 7 : campagne expérimentale avant test

### J31 : ablations ciblées

- **Construire :** exécuter sur dev les ablations ingestion/chunking/retrieval/vérification manquantes, une variable à la fois. Réutiliser les sorties sauvegardées lorsque les entrées sont identiques.
- **Livrable :** tableau d'ablations et coûts complets.
- **Vérifier :** chaque conclusion cite le run exact ; ne pas supprimer les variantes qui dégradent la qualité.

### J32 : sélection sur validation

- **Construire :** appliquer les candidats retenus aux 45 questions validation ; choisir configuration, budget et seuil d'abstention selon un objectif préécrit.
- **Livrable :** trois configurations finales : texte intégral, BM25 RAG et pipeline choisi ; règle de sélection publiée.
- **Vérifier :** aucune lecture des résultats test ; risque et couverture analysés ensemble. La validation réutilisée de nombreuses fois est signalée comme telle.

### J33 : diagnostic avec preuves oracle

- **Construire :** fournir les preuves annotées au générateur sur dev/validation pour distinguer défaut de retrieval et défaut de compréhension/génération.
- **Livrable :** typologie quantifiée des erreurs et cas illustrés.
- **Vérifier :** les performances oracle ne figurent pas comme celles du produit ; aucune annotation de réponse n'est passée au générateur par accident.

### J34 : latence, coût et variabilité

- **Construire :** mesures cache froid/chaud, composants/total, concurrence modérée ; répéter trois générations sur un sous-ensemble dev choisi à l'avance.
- **Livrable :** distributions de latence et coût, variation des réponses et échecs.
- **Vérifier :** GPU/CPU/API ne sont pas mélangés dans la même colonne ; effectifs et conditions publiés. Revoir le budget avant le test complet.

### J35 : gel de la release candidate

- **Construire :** tag ou commit identifié, manifeste global, prompts figés, archive des configs, plan d'analyse et de bootstrap. Relire les critères de succès et les limites.
- **Livrable :** release candidate reproductible.
- **Vérifier :** les trois systèmes finaux utilisent les mêmes questions et corpus ; décisions prises avant l'ouverture du test. Les défauts bloquants restants retardent J36.

**Jalon 7 :** on sait exactement ce que l'on va mesurer ; aucun objectif n'est choisi après avoir vu le résultat final.

## Semaine 8 : test final, rapport et publication

### J36 : exécution du test réservé

- **Construire :** lancer les trois systèmes finaux sur les 90 questions, plus variantes linguistiques et cas de robustesse réservés retenus. Conserver réponses brutes, contextes, erreurs et compteurs.
- **Livrable :** artefacts immuables du test et contrôle de complétude.
- **Vérifier :** aucun réglage des prompts après observation ; un bug invalidant une exécution impose une note de correction et un nouveau run identifié.

### J37 : annotation aveugle des réponses, première partie

- **Construire :** anonymiser les noms des systèmes ; annoter fidélité, complétude, décisions et citations sur environ la moitié des 270 réponses de base. Organiser la relecture des cas difficiles.
- **Livrable :** jugements structurés avec motifs et temps d'annotation.
- **Vérifier :** même grille pour toutes les réponses ; ne pas réécrire les références pour favoriser le pipeline complexe.

### J38 : annotation finale et statistiques

- **Construire :** terminer les annotations, résoudre les désaccords puis calculer différences appariées et intervalles par famille. Publier les effectifs et les échecs techniques.
- **Livrable :** tableaux finaux recalculables et courbes risque–couverture/coût.
- **Vérifier :** 270 réponses annotées est une charge réelle ; ajouter des journées si nécessaire. Les scores linguistiques et les petits sous-groupes gardent leurs limites statistiques.

### J39 : rapport technique et cas d'échec

- **Construire :** rédiger problème, source PDF, nettoyage, architecture, protocole, résultats, ablations, coûts et limites. Inclure au moins cinq échecs instructifs, dont un où une méthode simple gagne si ce cas existe.
- **Livrable :** rapport de 6 à 10 pages environ, README, data card et vidéo de 3 à 5 minutes.
- **Vérifier :** chaque chiffre renvoie à un artefact ; la langue, l'édition et la provenance des textes sont explicites ; une traduction générée n'est pas présentée comme une citation littérale.

### J40 : reproduction et version livrable

- **Construire :** test depuis un clone ou environnement neuf, reconstruction des tableaux sans appels API, démonstration d'une question avec clé externe, revue des fichiers publiables.
- **Livrable :** version `v1.0`, guide de lancement et liste des limites connues.
- **Vérifier :** les droits du PDF/traduction sont pris en compte ; publier acquisition/hash plutôt que redistribuer sans droit établi. Mettre à jour le CV seulement avec les capacités réellement réalisées et les résultats réellement mesurés.

**À J40, le projet est complet dans son périmètre.** L'extension suivante ne doit pas retarder cette livraison.

## J41 à J50 : une contribution de recherche supplémentaire

Choisir **une seule piste**, à partir des erreurs observées. Piste recommandée si les mesures la justifient : **décider quand un contexte simple suffit et quand dépenser davantage en retrieval/vérification**. Le but est de réduire le coût à qualité comparable, ou le risque à coût comparable.

Alternative : adaptation d'un reranker, seulement si l'erreur dominante vient du classement et si l'on peut constituer un vrai ensemble d'entraînement séparé. Le petit benchmark de 180 familles ne suffit pas à justifier à lui seul un entraînement profond fiable.

### J41 : hypothèse et protocole de l'extension

- **Construire :** écrire une hypothèse falsifiable, une baseline et un plafond de budget. Définir un nouveau test réservé puisque le test v1 a été inspecté.
- **Livrable :** protocole `v2` d'une page, critère de poursuite et de renoncement.
- **Vérifier :** la piste répond à un défaut mesuré, pas à l'envie d'ajouter une technologie.

### J42 : données de décision ou de classement

- **Construire :** pour le routage, collecter caractéristiques disponibles avant/après retrieval et issue de chaque stratégie sur dev/validation. Pour le reranker, construire un jeu d'entraînement supplémentaire avec groupes de questions et vrais positifs relus.
- **Livrable :** dataset de l'extension avec provenance et splits.
- **Vérifier :** aucune sortie du test v1 utilisée pour entraîner un modèle évalué ensuite comme inédit sur ce même test. Si les nouvelles données ne sont pas suffisantes, prolonger la collecte ou conserver une règle simple.

### J43 : baseline simple de la nouvelle décision

- **Construire :** routage par règle ou petit classifieur régularisé, avec validation groupée. Pour le reranker : comparaison modèle de base, optimisation sans entraînement et données supplémentaires.
- **Livrable :** résultat de référence et analyse des erreurs de décision.
- **Vérifier :** aucun signal issu de la réponse de référence n'est utilisé comme feature à l'inférence ; peu de données implique des conclusions prudentes.

### J44 : implémentation de la variante

- **Construire :** routage borné entre voie simple et voie approfondie ; ou entraînement du reranker si la porte de passage est satisfaite. Dans ce second cas, miner les négatifs uniquement depuis l'ensemble autorisé et regrouper les positifs des paraphrases identiques.
- **Livrable :** module isolé, configuration, logs et checkpoint si applicable.
- **Vérifier :** pas de faux négatif connu parmi les positifs de la même famille, budget borné et modèle/version identifiables.

### J45 : contrôle de généralisation

- **Construire :** validation groupée par famille/thème, courbes selon taille des données ; arrêter une variante qui surapprend sans bénéfice.
- **Livrable :** décision documentée de conserver, simplifier ou abandonner.
- **Vérifier :** baisse de loss ne vaut pas amélioration documentaire ; comparaisons à candidats et annotations identiques.

### J46 : stress test documentaire

- **Construire :** perturber des copies de dev : mauvais ordre des passages, preuves manquantes, erreurs d'extraction réalistes et distractions éditoriales.
- **Livrable :** étude de robustesse et cartes d'erreurs.
- **Vérifier :** conserver les PDF/texte authentiques immuables ; ne pas présenter des articles modifiés artificiellement comme une vraie version de la Constitution.

### J47 : compromis coût/qualité

- **Construire :** comparer la variante à « toujours simple » et « toujours approfondi », ou base/FT à budget comparable. Mesurer les appels et le coût réels.
- **Livrable :** courbe de compromis et configuration finale `v2` choisie sur validation.
- **Vérifier :** inclure dans le coût le routeur ou le vérificateur lui-même ; les gains de latence ne viennent pas d'un cache différent.

### J48 : test inédit de l'extension

- **Construire :** lancer sur les nouvelles familles réservées, annoter avec la même grille et comparer aux baselines figées.
- **Livrable :** artefacts et statistiques séparés de v1.
- **Vérifier :** si aucun nouveau test n'a pu être constitué, nommer les résultats exploratoires et ne pas les annoncer comme une validation indépendante.

### J49 : note de recherche

- **Construire :** rédiger la question, la méthode, les ablations, les coûts et ce qui n'a pas marché. Documenter les limites des données et de la relecture.
- **Livrable :** note courte publiable et figures régénérables.
- **Vérifier :** le titre reflète le résultat réel ; pas de promesse générale de « fiabilité juridique » à partir d'un seul PDF.

### J50 : publication et préparation de la soutenance

- **Construire :** release `v2` si justifiée, démonstration comparée, présentation de cinq minutes et réponses aux questions techniques.
- **Livrable :** explication défendable de tes choix, avec exemples et chiffres.
- **Vérifier :** pouvoir expliquer pourquoi le corpus est petit, quand le texte intégral gagne, comment une citation peut être fausse malgré un ID valide et pourquoi le test est séparé de la validation.

## Si le calendrier dérape

À reporter en premier : dialogue avancé, décomposition, graphe au-delà des renvois explicites, second fournisseur et extension d'entraînement. Le volet arabe est hors périmètre.

À conserver : traitement complet du PDF de référence, baseline texte intégral, évaluation séparée, citations vérifiables, abstention, sauvegarde des runs et installation reproductible.

La réussite du projet doit se formuler en capacités et preuves : « j'ai reconstruit et contrôlé les articles depuis un PDF complexe, comparé plusieurs stratégies de recherche et de contexte, puis mesuré la fidélité, la complétude, l'abstention et le coût ». Les valeurs numériques viendront des expériences.
