# Constitution Evidence : feuille de route d'un assistant documentaire juridique

Date de préparation : 23 septembre 2026. **Document de conception, pas compte rendu de travaux réalisés.**

## Le projet proposé

Construire un assistant à partir d'un **PDF officiel de référence de la Constitution marocaine**, capable de répondre avec des passages vérifiables, de réunir plusieurs articles lorsque nécessaire et de reconnaître une question à laquelle ses sources ne permettent pas de répondre. Le projet comprend toute la chaîne : extraction du PDF, nettoyage, reconstruction des articles, chunking, recherche et génération.

La question de recherche centrale : **quels mécanismes améliorent réellement la fiabilité des réponses, et à quel coût, face à une baseline qui reçoit le texte intégral ?**

La Constitution de **2011** est la version la plus récente identifiée dans les sources institutionnelles consultées le 23 septembre 2026 : [portail officiel Maroc.ma](https://maroc.ma/fr/le-maroc/constitution) et [fiche WIPO Lex, indiquée comme dernière version dans cette base](https://www.wipo.int/wipolex/en/legislation/details/13535). Le dossier [Sources PDF](sources.md) donne les liens et distingue version du texte, date du fichier et date de consultation.

## Les documents à suivre

1. **[Planning quotidien : 40 journées + 10 optionnelles](roadmap.md)** : tâches, livrables, contrôles et jalons.
2. **[Spécification technique](implementation-spec.md)** : architecture, modules, contrats de données, API et exécution.
3. **[Protocole d'évaluation](evaluation-protocol.md)** : benchmark, séparation des données, métriques, comparaisons et conditions de publication.
4. **[Sources PDF et version retenue](sources.md)** : choix du document français.

Le format reprend le dernier plan de [ChatGPT_proj.pdf](../../../ChatGPT_proj.pdf), notamment son rythme « construire, mesurer, consigner » et ses critères de passage. Les dates et les recommandations de candidature contenues dans ce PDF ne sont pas reprises comme des exigences actuelles.

## Temps et périmètre

- **Version complète : 40 journées de travail, environ 200 à 240 heures**, généralement 8 semaines à 5 journées. L'annotation peut prolonger ce calendrier.
- **Recherche supplémentaire : 10 journées, environ 50 à 60 heures**, après une première version publiée.
- À 2 heures par jour, prévoir environ 20 à 24 semaines pour le socle à raison de 5 journées par semaine.
- Périmètre évalué en français uniquement ; le volet arabe a été retiré à la demande du porteur du projet.
- Matériel : CPU pour ingestion, BM25 et API ; GPU facultatif pour accélérer embeddings/reranking et pour l'extension d'entraînement.
- Aucun abonnement, achat, appel API payant ou déploiement n'est lancé par cette feuille de route.

## Ce qui donnera de la profondeur au projet

| Dimension | Preuve attendue |
| --- | --- |
| Traitement du PDF | Extraction contrôlée, corrections traçables et comparaison de plusieurs stratégies de chunking |
| Fiabilité documentaire | Un clic relie une affirmation au bon extrait, à son article et au PDF source |
| Évaluation | Questions annotées, test réservé, sorties brutes et comparaison avec texte intégral |
| Raisonnement sur plusieurs passages | Couverture de toutes les preuves nécessaires, pas seulement du premier article pertinent |
| Abstention | Mesure des erreurs parmi les réponses effectivement délivrées, avec taux de réponse |
| Ingénierie | API, reprise après interruption, budgets, cache invalidable, tests et reproduction depuis un clone |
| Recherche optionnelle | Une expérience ciblée, contrôlée et publiable, y compris si elle ne montre aucun gain |

Sur ce petit corpus, une recherche exacte est suffisante pour commencer. Le nombre de frameworks, une base vectorielle distante ou un système multi-agents ne constituent pas des objectifs. Une expérience qui montre que le texte intégral fait mieux que le RAG est un résultat utile.

## Première action

Commencer par **J1 : fixer la source PDF et le contrat du produit**. Le premier livrable est une fiche d'une page décrivant le corpus, les questions prises en charge, les langues et les critères de réussite. Le code du nouveau projet pourra vivre dans un dépôt `constitution-evidence` ; ce dossier contient seulement sa préparation.

À la fin, les résultats publiés et la démonstration serviront à présenter les réalisations mesurées dans les candidatures.
