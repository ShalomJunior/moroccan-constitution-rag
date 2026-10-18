# État du benchmark v1

`data/annotations/questions.jsonl` contient actuellement les 15 questions de calibration déjà utilisées en développement. Elles sont conservées comme **brouillons** (`author_provisional`) : leurs articles associés ne constituent pas des preuves suffisantes relues et elles ne comptent pas comme annotations finales.

La commande `constitution-evidence audit-questions` affiche l'inventaire et les défauts de structure. Elle vérifie notamment les identifiants, la séparation des familles, les champs d'annotation et les offsets des preuves dans le corpus actif. Elle ne peut pas établir qu'une interprétation juridique est correcte. Le seuil prévu reste 45 familles dev, 45 validation et 90 test ; au démarrage de ce fichier, il manque donc 30, 45 et 90 familles respectivement, ainsi que la revue des 15 brouillons.

Pour chaque famille ajoutée, suivre [le guide d'annotation](annotation-guide.md), vérifier les preuves sur le PDF et le corpus canonique, puis seulement attribuer `review_status: "reviewed"`. Les questions test doivent être écrites et annotées avant le gel des configurations ; leurs sorties ne servent pas à choisir les méthodes. Une seconde passe par l'auteur doit être signalée comme telle si aucun autre relecteur n'est disponible.

Une fois l'audit complet, les expériences de recherche sur dev et validation peuvent être exécutées, la configuration sélectionnée sur validation, puis `release-readiness` doit être relancé. Aucun résultat de `v1.0` ne doit être annoncé tant que le test réservé et le jugement des réponses ne sont pas terminés.
