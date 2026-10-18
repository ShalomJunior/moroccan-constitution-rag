# Sources PDF et version de départ

[Accueil](README.md) · [Planning](roadmap.md)

Vérification effectuée le **23 septembre 2026**.

## Version à retenir

**Je recommande de partir de la Constitution de 2011 dans une publication institutionnelle.** C'est la version la plus récente identifiée dans les sources consultées : le portail officiel Maroc.ma la propose dans sa page Constitution ; WIPO Lex affiche sa fiche comme dernière version disponible dans sa base. Aucune Constitution plus récente n'a été identifiée pendant cette recherche. Sources : [Maroc.ma](https://maroc.ma/fr/le-maroc/constitution), [WIPO Lex](https://www.wipo.int/wipolex/en/legislation/details/13535).

Une date récente dans l'URL ou dans les métadonnées du PDF peut être une date de mise en ligne. Elle ne doit pas être interprétée comme la date d'une nouvelle Constitution. Par exemple, le chemin du PDF de Maroc.ma contient `2024-10` et son nom fait référence à 2011.

## Liens utilisables

| Source | Lien | Utilisation et état de vérification |
| --- | --- | --- |
| Secrétariat général du gouvernement | [Constitution, édition 2011, PDF français](https://www.sgg.gov.ma/Portals/0/constitution/constitution_2011_Fr.pdf) | Premier choix pour le socle français ; document identifié par recherche, ouverture complète expirée pendant cette préparation |
| Portail officiel du Royaume | [Page Constitution](https://maroc.ma/fr/le-maroc/constitution) | Page ouverte ; contient le lien de téléchargement officiel |
| Portail officiel du Royaume | [PDF de la Constitution](https://maroc.ma/sites/default/files/2024-10/constitution_du_1er_juillet_2011.pdf) | Lien suivi et document reconnu comme PDF de 28 pages ; couche texte non restituée par l'outil web, qualité/langue à contrôler à l'ingestion |
| Organisation mondiale de la propriété intellectuelle | [Fiche WIPO Lex de la Constitution de 2011](https://www.wipo.int/wipolex/en/legislation/details/13535) | Fiche ouverte ; utile au contrôle de version de l'édition française |

Sur WIPO Lex, utiliser le lien **français associé à 2011**. La fiche signale que le texte anglais proposé à titre de référence est celui de 1996 : ne pas le mélanger avec le corpus 2011. Les téléchargements WIPO peuvent utiliser des liens temporaires ; passer par la fiche pour les régénérer. [Source : fiche WIPO Lex](https://www.wipo.int/wipolex/en/legislation/details/13535).

## Décision pour le plan

1. **Socle : français**, PDF institutionnel de la Constitution de 2011, édition et fichier figés par hash.
2. **Langue : français uniquement** ; aucune extension arabe n'est prévue dans ce projet.
3. Toute la chaîne est implémentée à partir des PDF : extraction, nettoyage, structure, découpage, indexation et citation.
4. Le modèle répond dans le périmètre du texte chargé ; les lois d'application et la jurisprudence ne sont pas implicitement incluses.

Le choix définitif du fichier français se fait à J1 après téléchargement : privilégier une publication lisible et attribuable. Ne pas déclarer un PDF scanné uniquement parce qu'un outil web n'en restitue pas le texte ; tester sa couche texte localement à J2.

## Manifeste à enregistrer

```yaml
document: Constitution du Royaume du Maroc
text_version: '2011'
language: fr
source_page: URL_DE_LA_PAGE_INSTITUTIONNELLE
download_url: URL_EFFECTIVEMENT_UTILISEE
downloaded_at: HORODATAGE_UTC
sha256: HASH_DU_FICHIER
page_count: NOMBRE_VERIFIE
extraction_method: A_DETERMINER_APRES_DIAGNOSTIC
```

Ce manifeste décrit le fichier réellement ingéré. Il ne doit pas être prérempli avec un hash ou une langue déduits d'un autre document.
