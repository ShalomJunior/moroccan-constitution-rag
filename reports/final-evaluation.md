# Évaluation finale sur le test réservé

**État :** résultats calculés sur le test réservé français de 90 questions. Le code, le corpus, les questions, les trois systèmes et le plan d'analyse ont été gelés avant cette exécution au commit `726abe0632f027dd430e4bac405ca0b66513b8c6`. Le corpus porte l'empreinte `5a735fe19fc74d8d9e0f45d664066ec1ce1a423e4dcc68f805ab59190444e0cd`. Les questions, réponses individuelles et la correspondance des systèmes restent dans `runs/`, hors du dépôt public.

## Méthode

Les trois systèmes ont utilisé le même Qwen3-4B (`Qwen/Qwen3-4B`, révision `1cfa9a7208912126459214e8b04321603b3df60c`, quantification bitsandbytes NF4) sur Kaggle T4 x2 : texte intégral, BM25 RAG et pipeline hybride sélectionné sur la validation. Les 90 questions de test ont produit une ligne par système. Une erreur technique vaut un échec, sans substitution ni relance ciblée. La personne responsable du projet a fourni les jugements aveugles des 205 réponses sans erreur technique ; les 65 erreurs techniques ont été comptées automatiquement comme échecs. Les jugements portent sur la décision de répondre ou de s'abstenir, la fidélité des affirmations, l'exhaustivité et la justesse des citations. Le succès strict exige les quatre critères positifs. Les intervalles des différences utilisent 2 000 rééchantillonnages appariés par famille, selon le plan préenregistré.

| Système | Succès strict / 90 | Couverture des réponses | Risque parmi les réponses | Erreurs techniques |
| --- | ---: | ---: | ---: | ---: |
| BM25 RAG | 51 / 90 (56,7 %) | 69 / 90 (76,7 %) | 15 / 69 (21,7 %) | 11 / 90 (12,2 %) |
| Texte intégral | 25 / 90 (27,8 %) | 46 / 90 (51,1 %) | 20 / 46 (43,5 %) | 35 / 90 (38,9 %) |
| Pipeline hybride sélectionné | 51 / 90 (56,7 %) | 67 / 90 (74,4 %) | 16 / 67 (23,9 %) | 19 / 90 (21,1 %) |

La différence de succès strict « hybride moins BM25 » est de **0 point** (IC à 95 % : −8,9 à +8,9 points). « Texte intégral moins BM25 » vaut −28,9 points (IC à 95 % : −40,0 à −17,8 points). Le résultat ne démontre pas une amélioration du pipeline hybride par rapport à BM25 sur ce test. Le texte intégral a une couverture et un succès strict plus faibles, avec davantage d'erreurs techniques.

Les erreurs techniques proviennent surtout de citations dont la chaîne ne correspond pas exactement au passage fourni : 23 pour le texte intégral, 10 pour BM25 et 14 pour l'hybride. Le modèle a aussi produit un JSON invalide dans 7, 1 et 5 cas respectivement. Ces sorties ont été rejetées par les contrôles de l'application. Aucune des 90 lignes du nouveau texte intégral n'a échoué par manque de mémoire GPU. Les temps cumulés enregistrés sont d'environ 8,94 h pour le texte intégral, 0,60 h pour BM25 et 0,80 h pour l'hybride ; ils comprennent des charges différentes et ne constituent pas un comparatif de latence à matériel et charge égaux.

## Limites et traçabilité

Cette mesure concerne ce corpus français, ces 90 questions et ce modèle ; elle n'établit pas une fiabilité juridique générale. La revue des réponses repose sur une seule personne et n'a pas de mesure d'accord entre annotateurs. Le risque parmi les réponses désigne ici une affirmation non fidèle **ou** une citation jugée incorrecte ; il ne compte pas une réponse seulement incomplète comme une affirmation fausse. La courbe risque–couverture prévue reste indisponible, car les réponses n'ont pas de score de confiance comparable. Les erreurs observées sur le test réservé ne doivent pas servir à sélectionner rétroactivement un modèle ou un prompt pour ce même test.

Le résumé du fichier de revue annonçait 124 réponses entièrement validées et 81 en échec. Ses 205 lignes détaillées, complétées par le jugement `B0270` fourni séparément, indiquent **127** validations et **78** échecs. Les scores ci-dessus utilisent les jugements individuels, vérifiés par identifiant aveugle et identifiant de question. La règle qui dérive le champ `unsupported_or_incorrect` des quatre critères est conservée avec les jugements privés.

Empreintes privées de reproduction : archive Kaggle `ea5061aaa6068530a5ebdc3b3553c643852e28bfd814803797ef491fef62ab53` ; correspondance aveugle `d289e567a5749a6d4b69894d7b05cafab8db2352c2d38d2c378367c3104a08cb` ; jugements finalisés `0bd5b2f69d9bc686b1d8de137c54fdfaab83998b1c57d9fd8877528483d38825`. Les scores détaillés et la provenance sont conservés sous `runs/final-blind-review-20261022/` et ne doivent pas être publiés avec les questions réservées.
