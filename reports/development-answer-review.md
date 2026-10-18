# Revue des réponses de développement

Deux séries de 15 questions françaises ont été posées à Groq avec le même corpus corrigé (empreinte des articles : `c319ecb4cabe0eaafc3de18779cc210ec8fa83cffbaeb2259393073e9fb4901c`). Le propriétaire du projet a vérifié, pour chaque réponse, la décision de répondre ou de s'abstenir, l'appui de chaque affirmation, la complétude et les citations.

| Série | Réponses satisfaisant les quatre critères |
| --- | ---: |
| Première génération | 7/15 |
| Après ajout des alinéas voisins et des citations multiples | 8/15 |

La première série omettait notamment les conditions de l'article 24 et citait des points de liste sans leur chapeau dans les articles 49 et 92. Ces trois cas ont été corrigés dans la seconde série. D'autres défauts sont restés ou sont apparus : extrapolation depuis l'article 6, réponses incomplètes sur les articles 27 et 25, contresens sur la protection du droit à la vie, et deux citations rejetées parce qu'elles ne correspondaient pas exactement aux passages fournis.

Le validateur empêche de présenter une citation inventée comme une citation exacte. Il ne sait pas établir qu'une affirmation est juridiquement fondée ni que tous les éléments de la question ont été traités. Les deux séries servent à décrire ces limites et à corriger des défauts techniques. Avec 15 questions de développement et sans test indépendant, la différence de 7 à 8 réponses ne démontre pas un gain général de qualité.

Les textes du corpus actif ne contiennent pas les anciennes chaînes OCR suspectées dans les notes de revue (`une: égale`, `situation familiale,` et plusieurs coquilles des articles 141 à 146). Les citations candidates rejetées n'ayant pas été enregistrées, leur échec précis ne peut pas être attribué à ces coquilles. Une revue juridique indépendante et le benchmark final restent à faire avant toute revendication de fiabilité générale.
