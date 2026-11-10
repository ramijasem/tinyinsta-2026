# Notes de mise en place

## Montage
- Projet GCP : tinyinsta-2026-511514 — région App Engine : europe-west
- URL : https://tinyinsta-2026-511514.ew.r.appspot.com
- Version par défaut : 20261106t175435 (déployée le 06/11/2026), app.yaml : F1, autoscaling max 10 instances
- Base : Firestore en mode Datastore (DATASTORE_MODE), concurrencyMode = PESSIMISTIC
- Index composite Post(author ASC, created DESC) : READY
- Client de charge et de seed : Cloud Shell (Python 3.12, locust 2.46.7, google-cloud-datastore 2.19.0)
- Vérification initiale : /api/timeline?user=test -> {"count":0,...}, en-têtes X-Instance et Server-Timing présents

## Génération des jeux (chronologie)
### 06/11 (gRPC, 6 threads par défaut)
- base : 21000 entités en 40.7 s (517/s) — OK
- u100 : 2100 en 1.4 s — OK
- u10000 : DeadlineExceeded répétés, interrompu (Ctrl+C) -> jeu partiel
- p10 : 1100 en 1.1 s ; p100 : 10100 en 4.0 s — OK
- p1000 : ServiceUnavailable + DeadlineExceeded -> RuntimeError "lot abandonné après 6 essais" -> jeu partiel
- f05 … f100 : 20 jeux x 2520 entités, sans erreur — OK
- Purge p1000 : 92000 entités. Purge u10000 : échec (DeadlineExceeded sur la requête de listage, timeout client 60 s), puis 59500 supprimées à la 2e tentative
- Reseed avec --threads 2 : interrompu par une déconnexion Cloud Shell -> p1000 = 26400 posts, u10000 = 51000 posts
- Purge par défaut en échec (listage > 60 s) ; purge avec timeout 300 s : p1000 26500, u10000 61000 entités supprimées
- Reseed p1000 --threads 2 (nohup) : DeadlineExceeded en boucle -> arrêté
### 07/11
- p1000 contenait 49400 posts -> purge (49500 entités)
- Reseed p1000 --threads 1 (gRPC) : DeadlineExceeded répétés, > 50 min -> arrêté
### 08/11 (option --rest du script)
- Purge p1000 --rest : 46000 entités
- p1000 --rest : 100100 entités en 28.8 s (3475/s), 0 erreur
- u10000 --rest : 210000 entités en 68.2 s (3080/s), 0 erreur
- Vérification des 27 jeux (bench/check_datasets.py) : u100 = 4000 posts (x2, seed lancé deux fois)
  -> purge u100 (4100 entités) + reseed --rest (2100 en 1.4 s)
- Résultat final : 27/27 jeux exacts (U users, U*P posts)

## Analyse des incidents (pour la section Validité)
- Un seul facteur changé (gRPC -> REST) : seed bloqué > 50 min -> 28.8 s sans erreur.
  Cause = transport gRPC depuis Cloud Shell (timeout client de 60 s sur commit/run_query), pas la capacité d'écriture de Datastore.
- Risque de doublons : les posts ont des clés incomplètes (mutation insert, commit non transactionnel).
  Un commit expiré côté client peut avoir été appliqué côté serveur ; le retry réécrit alors les posts. En REST, pas de timeout client par défaut.
- Mode PESSIMISTIC : les limites legacy (25 entity groups, 1 écriture/s par groupe) ne s'appliquent pas.
- Purges lentes : requêtes sur des plages fraîchement supprimées (tombstones). Attendre plusieurs heures entre la fin des seeds/purges (08/11 16h30) et les mesures de la Partie 1.
- Le seed n'influence pas les mesures : il remplit la base, l'application mesurée (main.py sur App Engine) a son propre client.

## Coût (à compléter avec la page Facturation)
- Écritures du seed final : ~400 000 entités, plus les écritures et suppressions des tentatives ratées (environ 300 000 entités supplémentaires)

## Chemin de code de get_timeline (vérifié le 10/11)
- hasattr(datastore.Client, 'gql') == False -> le chemin GQL (main.py L52-56) n'est JAMAIS exécuté ; le README est trompeur.
- Test direct de la requête de L61-64 sur f30 : 30 valeurs dans IN -> OK (20 posts) ; 31 valeurs -> InvalidArgument 400 "IN supports up to 30 values".
- Donc F <= 29 (F+1 <= 30 auteurs) : chemin IN (L61-64). F >= 30 : exception avalée (L65) -> boucle de F+1 requêtes séquentielles (L66-72), jusqu'à (F+1)*20 lectures, tri en Python. Réponse HTTP 200 dans les deux cas.
