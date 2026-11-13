# TinyInsta passe-t-elle à l'échelle ? — Benchmark 2026

Rapport du projet Données massives et Cloud. Sujet : [SUJET.md](SUJET.md). README d'origine du dépôt : [README_original.md](README_original.md).

## 1. Montage
- Projet GCP : `tinyinsta-2026-511514`, région App Engine : `europe-west`
- Application : https://tinyinsta-2026-511514.ew.r.appspot.com (version par défaut `20261106t175435`, F1, autoscaling ≤ 10)
- Base : Firestore en mode Datastore, `concurrencyMode = PESSIMISTIC`, index `Post(author ASC, created DESC)`
- Jeux de données : générés du 06/11 au 08/11/2026 avec `bench/seed_exact.py`, vérifiés par `bench/check_datasets.py` (27/27 exacts)
- Client (seed et charge) : Cloud Shell — Python 3.12, locust 2.46.7, google-cloud-datastore 2.19.0
- Versions de mesure : *(à compléter : fixed1, fixed2, fixed4, dates)*

## 2. Résultats

### Partie 1 — Coût d'une requête

#### Hypothèse

Avant de mesurer, je regarde ce que fait vraiment une timeline dans `get_timeline` (`main.py`, L38-73).

**Ce que fait le code.** Trois étapes :
1. un lookup par clé de l'utilisateur (L43) pour récupérer sa liste `follows` ;
2. l'ajout de l'utilisateur lui-même à cette liste (L47), soit F + 1 auteurs ;
3. une requête `author IN (...) ORDER BY created DESC LIMIT 20` (L61-64), servie par l'index composite `Post(author, created DESC)`.

Le code prévoit aussi une version GQL (L52-56), mais elle ne tourne jamais : `datastore.Client` n'a pas de méthode `gql` (vérifié). Et il y a un piège : si la requête `IN` échoue, l'erreur est ignorée (L65) et le code fait une boucle d'une requête par auteur (L66-72). Or Datastore accepte au plus 30 valeurs dans un `IN`. J'ai testé : 30 passe, 31 renvoie `400 IN supports up to 30 values`. Dès F = 30, l'application change donc de chemin sans rien dire, et répond toujours 200.

**U et P : je m'attends à un temps constant.**
Datastore range ses données par plages de clés triées (*range partitioning*). Dans l'index, les posts d'un même auteur sont côte à côte, du plus récent au plus ancien. Pour avoir ses 20 derniers posts, il suffit d'aller au début de sa plage et de lire 20 entrées : c'est la *range query* avec `ORDER BY … LIMIT` que le cours décrit comme naturelle en range partitioning. Le lookup de L43 est un accès par clé exacte (*point lookup*). Ni le nombre total d'utilisateurs (U), ni les posts plus anciens (P) n'entrent en jeu. C'est toute la différence avec le *Seq Scan* + *Sort* de PostgreSQL vu en cours : ici, on fait toujours l'équivalent d'un *Index Scan*.

**F : je m'attends à ce que ça ne passe pas à l'échelle.**
Chaque auteur suivi est une plage différente, potentiellement sur un *shard* différent. La requête devient un *scatter/gather* sur F + 1 plages, suivi d'une fusion des résultats.
- F ≤ 25 : une seule requête `IN`, légère hausse avec F ;
- F = 30 : un saut, le code bascule sur la boucle ;
- F ≥ 30 : F + 1 allers-retours successifs vers Datastore. Le temps devrait croître à peu près linéairement avec F.

Petit calcul de ce que coûte une timeline :

| Cas | Lookups | Requêtes Datastore | Posts renvoyés (max) |
|---|---|---|---|
| U ou P quelconque (F = 20) | 1 | 1 | 20 |
| F = 25 | 1 | 1 | 20 |
| F = 30 | 1 | 31 | 620 |
| F = 100 | 1 | 101 | 2 020 |

**Latence client.** `Server-Timing` ne chronomètre que `get_timeline` (L139-141). Tout le reste s'ajoute côté client : JSON, Flask, load balancer de Google, réseau jusqu'à Cloud Shell. Comme ça ne dépend ni de U, ni de P, ni de F, l'écart entre latence client et temps serveur devrait rester à peu près constant.

**En résumé :** ça devrait passer à l'échelle en U et en P grâce à l'index, mais pas en F, à cause du `IN` limité à 30 et de la boucle de secours. Comme le dit le cours : *« it scales if the data access scales »*.

#### Protocole
*(à compléter)*

#### Figures
*(fig1a, fig1b)*

#### Interprétation
*(à compléter)*

### Partie 2 — Capacité
#### Hypothèse
#### Protocole
#### Figures
#### Interprétation

### Partie 3 — Corriger et re-mesurer
#### Hypothèse
#### Protocole
#### Figures
#### Interprétation

## 3. Tableau des verdicts

| Dimension | Passe à l'échelle ? | Jusqu'où ? | Pourquoi (mécanisme) | Preuve |
|---|---|---|---|---|
| Utilisateurs (U) | | | | Fig. 1a |
| Posts par utilisateur (P) | | | | Fig. 1a |
| Followees (F) | | | | Fig. 1b |
| Instances (N) | | | | Fig. 2a |

## 4. Validité
1. Instances ayant réellement servi chaque mesure :
2. Indépendance des runs et ordre des mesures :
3. Part de la latence due au réseau :
4. Échecs comptés et codes HTTP observés :
5. Vérification du chemin de code : chemin GQL jamais exécuté ; `IN` limité à 30 valeurs (voir NOTES.md)
6. Coût de la campagne :

## 5. Coût de la campagne
*(à compléter avec la page Facturation)*
