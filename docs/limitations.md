# Limites de la version 1.0.0

Le projet porte sur une seule source : le PDF français de la Constitution marocaine de 2011. Il ne couvre ni les lois d'application, ni la jurisprudence, ni les changements ultérieurs du droit. Les réponses ne sont pas des conseils juridiques.

Le corpus français a été comparé au PDF et corrigé par le propriétaire du projet. Cette relecture unique améliore la transcription, mais ne garantit pas l'absence de toute erreur. Les liens vers les pages du PDF permettent de vérifier le texte source.

BM25, la recherche dense et la recherche hybride proposent des passages ; aucun mode ne garantit que tous les passages nécessaires ont été retrouvés. Une citation exacte prouve que les mots figurent dans le passage fourni, pas que l'affirmation générée en découle ou qu'elle est complète. Le système peut donc s'abstenir et une réponse apparemment bien citée peut rester incorrecte.

Le [test réservé final](../reports/final-evaluation.md) a mesuré trois systèmes Qwen3-4B sur 90 questions françaises. BM25 RAG et le pipeline hybride ont chacun réussi strictement 51 questions ; le texte intégral en a réussi 25. Parmi les réponses formulées, 15/69 pour BM25, 16/67 pour l'hybride et 20/46 pour le texte intégral comportaient une affirmation non fidèle ou une citation incorrecte. Les erreurs techniques et les abstentions injustifiées réduisent aussi la couverture utile. Cette étude à un seul relecteur ne certifie pas la fiabilité générale de l'application, et son mode Groq n'a pas été évalué dans ce test.

Le PDF et les modèles ne sont pas inclus dans le dépôt. Les utilisateurs récupèrent le PDF depuis sa source institutionnelle et vérifient les conditions de redistribution avant d'en republier le texte ou les dérivés.
