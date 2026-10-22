# Évaluation finale sur le test réservé

Le code, le corpus, les questions, les trois systèmes et le plan d'analyse ont été gelés avant l'exécution au commit `726abe0632f027dd430e4bac405ca0b66513b8c6`. L'empreinte du corpus est `5a735fe19fc74d8d9e0f45d664066ec1ce1a423e4dcc68f805ab59190444e0cd`. Les questions, réponses individuelles et correspondances aveugles restent privées sous `runs/`.

## Périmètre et méthode

L'étude porte sur la version française de la Constitution marocaine de 2011, pas sur sa version arabe ni sur le droit ultérieur. Le PDF institutionnel numérisé compte 28 pages et porte l'empreinte SHA-256 `4101d45b4733a6b36eee77bd9ef4175b23160103089b003b13907e8b6d59333d`. Poppler et Tesseract produisent le texte ; les corrections OCR sont ancrées aux pages du PDF. Le corpus comprend le préambule et 180 articles. La [fiche des données](../docs/data-card.md) décrit sa provenance et ses limites de redistribution.

Le benchmark comprend 45 familles de développement, 45 de validation et 90 de test réservé. La récupération hybride a été choisie sur la validation : sur 39 questions répondables, tous les passages nécessaires étaient présents dans le contexte de 37 questions pour l'hybride, 34 pour BM25 et 32 pour le dense seul. Sur le test, les trois systèmes utilisent le même Qwen3-4B (`Qwen/Qwen3-4B`, révision `1cfa9a7208912126459214e8b04321603b3df60c`) quantifié en NF4 sur Kaggle T4 x2. Le texte intégral utilise YaRN à 65 536 tokens et un préremplissage par blocs de 512 tokens ; BM25 RAG et l'hybride fournissent des passages plus courts. Les réglages figurent dans `configs/final_systems.json`. Le mode Groq de l'interface ne fait pas partie de cette comparaison.

Chaque système a produit une ligne pour chacune des 90 questions. Le validateur vérifie la structure de la réponse, l'identité et les bornes des passages cités, ainsi que la correspondance exacte de la citation avec le contexte fourni. Une sortie rejetée par ce validateur est une **erreur technique** et compte comme échec. Il y en a 65 sur 270 essais. Les 205 autres réponses ont été mélangées et revues sans nom de système par un second relecteur. Sa revue catégorielle, fournie en CSV et JSONL, est la référence finale de ce rapport. Elle juge le texte des affirmations, même lorsque la citation associée est correcte. Les 205 lignes revues correspondent exactement aux réponses du paquet aveugle ; les fichiers privés et leurs empreintes sont conservés pour le recalcul.

La revue distingue sept verdicts. Un **succès sans réserve** est une réponse `correct` ou une abstention `abstention_correct`. Une réponse **acceptable** inclut aussi `correct_minor_issues`. Les erreurs techniques comptent comme échecs dans les deux mesures. La nouvelle revue ne donne pas quatre booléens séparés pour la décision, la fidélité, la complétude et les citations : ces deux mesures sont donc des dérivations explicites des verdicts, pas une reconstitution fictive de l'ancienne grille. Les intervalles à 95 % des différences sont issus de 2 000 rééchantillonnages appariés par famille, avec la graine `20261018`.

## Résultats

| Système | Sans réserve / 90 | Acceptables / 90 | Réponses formulées / 90 | Erreurs techniques / 90 |
| --- | ---: | ---: | ---: | ---: |
| BM25 RAG | 51 (56,7 %) | 56 (62,2 %) | 69 (76,7 %) | 11 (12,2 %) |
| Texte intégral | 25 (27,8 %) | 34 (37,8 %) | 46 (51,1 %) | 35 (38,9 %) |
| Hybride sélectionné | 50 (55,6 %) | 57 (63,3 %) | 67 (74,4 %) | 19 (21,1 %) |

Sur les 205 réponses revues, 120 sont correctes, 21 correctes avec réserves mineures et six sont des abstentions justifiées, soit **147 acceptables (71,7 %)**. Les 58 autres se répartissent en 24 partiellement correctes, 13 incorrectes, quatre affirmations qui répètent seulement la question et 17 abstentions injustifiées. Parmi les réponses effectivement formulées, le relecteur en rejette 15/69 pour BM25, 14/46 pour le texte intégral et 12/67 pour l'hybride. Cette proportion d'**inacceptables parmi les réponses** n'est pas l'ancien indicateur « affirmation non fidèle ou citation incorrecte » : elle inclut aussi les réponses incomplètes et les non-réponses formulées.

Sur la mesure sans réserve, l'hybride moins BM25 vaut −1,1 point (IC 95 % : −11,1 à +8,9), le texte intégral moins BM25 −28,9 points (−41,1 à −17,8), et l'hybride moins le texte intégral +27,8 points (+15,6 à +40,0). Sur la mesure acceptable, l'hybride moins BM25 vaut +1,1 point (−7,8 à +10,0). Ces intervalles ne montrent pas de gain établi de l'hybride face à BM25. La récupération plus complète mesurée sur la validation ne s'est pas traduite par un meilleur succès sans réserve sur ce test.

Le contrôle automatique a rejeté 47 citations dont la chaîne ne correspondait pas exactement au passage fourni : 23 pour le texte intégral, dix pour BM25 et 14 pour l'hybride. Il a aussi rejeté du JSON invalide dans sept, un et cinq cas respectivement. Ces erreurs appartiennent aux 65 sorties techniques, hors des 205 jugements humains. L'affirmation du relecteur selon laquelle les citations sont exactes concerne les 205 réponses examinées, et ne contredit pas ces rejets automatiques. Aucun des 90 essais du texte intégral n'a échoué par manque de mémoire GPU. Les temps cumulés sont d'environ 8,94 h pour le texte intégral, 0,60 h pour BM25 et 0,80 h pour l'hybride ; les charges diffèrent et ces sommes ne mesurent pas une latence de service comparable.

## Échecs et limites

La Constitution fournissait une réponse pour 17 des 23 abstentions produites sans erreur technique. Une réponse a cité l'article 179 dans sa limitation tout en refusant de répondre ; une autre a ignoré l'abrogation de la Constitution de 1996 à l'article 180. Cinq affirmations contredisent leur propre citation, notamment sur l'indépendance des instances de bonne gouvernance. Quatre répètent la question au lieu d'y répondre. Ces exemples montrent pourquoi l'exactitude textuelle d'une citation ne suffit pas à valider le sens de l'affirmation.

Le relecteur a trouvé 13 questions sans réponse acceptable parmi les 85 questions représentées dans les 205 sorties examinées. Cinq autres questions (`test-047`, `test-048`, `test-064`, `test-072`, `test-082`) n'avaient que des erreurs techniques et ne figuraient donc pas dans son paquet : **18 des 90 questions** n'ont aucune réponse acceptable dans le test complet. Ce nombre décrit les trois systèmes réunis ; il ne signifie pas que chaque système échoue sur les mêmes questions.

Le corpus a été comparé au PDF par une seule personne ; la revue finale des réponses repose sur un seul autre relecteur. Aucun accord interannotateurs n'est mesuré. Un seul échantillon généré par système et par question a été testé. La courbe risque–couverture reste indisponible faute de scores de confiance comparables. Ces résultats ne certifient ni l'application web ni une fiabilité juridique générale. Les erreurs du test réservé ne doivent pas servir à modifier rétroactivement le système évalué ; toute correction future exige de nouvelles questions de validation.

## Reproduction

Le dépôt public contient le code, le verrou des dépendances, les configurations, le journal de corrections et ce rapport. Il ne redistribue ni le PDF, ni le corpus OCR dérivé, ni les questions et réponses réservées. Le [guide de reproduction](../docs/reproduction.md) décrit la reconstruction locale. Depuis les trois fichiers privés (`packets.jsonl`, `private_mapping.jsonl`, `authoritative-review.jsonl`), `constitution-evidence score-review-verdicts --packets ... --mapping ... --reviews ...` recalcule les agrégats sans appel au modèle. Empreintes SHA-256 : paquet `40788b1057b9ab1e4ee7c6154da7fca383b467dab8b916f6fefe61ce61f240c4`, correspondance `d289e567a5749a6d4b69894d7b05cafab8db2352c2d38d2c378367c3104a08cb`, revue JSONL `d45603bfade3d465e98782fadf81e25fab253602d4020b8d477aee3cc10883ea`.

La version du code publiée après le test ne change pas le commit gelé `726abe0632f027dd430e4bac405ca0b66513b8c6`. Une reproduction stricte de la génération doit partir de ce commit et de son bundle privé. Les calculs de score, eux, peuvent être refaits avec le code actuel et les fichiers privés conservés localement.
