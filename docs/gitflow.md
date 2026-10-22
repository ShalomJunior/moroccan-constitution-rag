# Gitflow

`main` contient les versions publiées et `develop` intègre les fonctionnalités en cours. Les contributions utilisent des pull requests et passent la CI avant intégration.

| Branche | Origine | Destination |
| --- | --- | --- |
| `feature/<nom>` ou `fix/<nom>` | `develop` | `develop` |
| `release/<version>` | `develop` | `main`, puis retour vers `develop` |
| `hotfix/<nom>` | `main` | `main`, puis retour vers `develop` |

Chaque version publiée porte un tag `vMAJOR.MINOR.PATCH`. Une pull request décrit le changement, les vérifications effectuées et son éventuel impact sur les données ou l'évaluation. Les réglages du test réservé sont figés avant son exécution ; toute expérience ultérieure est distincte de ce test.

Les clés, PDF téléchargés, modèles, corpus générés, annotations complètes et résultats individuels restent hors du dépôt. Les configurations et les rapports agrégés sont versionnés.
