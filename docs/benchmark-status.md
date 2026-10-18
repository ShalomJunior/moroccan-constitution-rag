# État du benchmark v1

`data/annotations/questions.jsonl` contient 45 questions de développement en **brouillon** (`author_provisional`) : les 15 questions de calibration déjà utilisées et 30 nouvelles questions candidates. Les articles proposés sont dans `candidate_articles`. Ils ne constituent pas des preuves suffisantes relues et ne comptent pas comme annotations finales.

La commande `constitution-evidence audit-questions` affiche l'inventaire et les défauts de structure. Elle vérifie notamment les identifiants, la séparation des familles, les champs d'annotation et les offsets des preuves dans le corpus actif. Elle ne peut pas établir qu'une interprétation juridique est correcte. Le seuil prévu reste 45 familles dev, 45 validation et 90 test : les 45 questions dev doivent être relues, et les 45 validation et 90 test restent à rédiger et relire.

`constitution-evidence question-review-packet` crée `reports/question-review.md`, un dossier de travail local avec les questions dev, les articles candidats, le texte canonique et les liens vers les pages du PDF. Ce dossier est ignoré par Git. Il ne valide aucune question automatiquement.

Pour chaque famille ajoutée, suivre [le guide d'annotation](annotation-guide.md), vérifier les preuves sur le PDF et le corpus canonique, puis seulement attribuer `review_status: "reviewed"`. Les questions test doivent être écrites et annotées avant le gel des configurations ; leurs sorties ne servent pas à choisir les méthodes. Une seconde passe par l'auteur doit être signalée comme telle si aucun autre relecteur n'est disponible.

Une fois l'audit complet, les expériences de recherche sur dev et validation peuvent être exécutées, la configuration sélectionnée sur validation, puis `release-readiness` doit être relancé. Aucun résultat de `v1.0` ne doit être annoncé tant que le test réservé et le jugement des réponses ne sont pas terminés.
