# Point d'entrée unique du benchmark TinyInsta.
#   make            -> régénère toutes les figures et leurs CSV depuis raw/ (gratuit, sans cloud)
#   make check      -> vérifie que les 27 jeux ont exactement U users et U*P posts
#   make seed CONFIRM=oui   -> purge puis repeuple les 27 jeux (écritures Datastore facturées)
#   make part1 | part2 | part3   -> relance les mesures d'une partie (instances B1 facturées,
#                                   arrêtées automatiquement à la fin, même en cas d'erreur)
#   make stop       -> arrête toutes les versions de mesure
# Les cibles longues se lancent de préférence avec nohup (Cloud Shell coupe les sessions inactives).
SHELL := /bin/bash
.RECIPEPREFIX = >
P ?= $(shell gcloud config get-value project 2>/dev/null)
SEED := python bench/seed_exact.py --project $(P) --rest
RUN ?= run1

# préfixe:U:P:F (section 2 du sujet)
DATASETS := base:1000:20:20 u100:100:20:20 u10000:10000:20:20 \
            p10:100:10:20 p100:100:100:20 p1000:100:1000:20 \
            $(foreach f,05 10 15 20 25 30 35 40 45 50 55 60 65 70 75 80 85 90 95 100,f$(f):120:20:$(f))

.PHONY: figures check seed part1 part2 part3 mesures stop
figures:
> python bench/make_figures.py

check:
> python bench/check_datasets.py

seed:
> @test "$(CONFIRM)" = oui || { echo "Purge puis repeuple les 27 jeux : relancer avec  make seed CONFIRM=oui"; exit 1; }
> set -e; for d in $(DATASETS); do IFS=: read px u p f <<< "$$d"; \
>   $(SEED) --prefix $$px --purge; \
>   $(SEED) --prefix $$px --users $$u --posts-per-user $$p --followees $$((10#$$f)); \
> done
> python bench/check_datasets.py

part1:
> gcloud app versions delete fixed1 --quiet 2>/dev/null || true; \
> trap 'gcloud app versions stop fixed1 --quiet' EXIT; \
> ./deploy_fixed.sh 1 && bench/run_part1.sh

part2:
> set -e; for n in 1 2 4; do bench/run_part2.sh $$n; done

part3:
> bench/run_part3.sh 1 && rm -rf raw/part3/n1_$(RUN) && mv raw/part3/n1 raw/part3/n1_$(RUN)

mesures: part1 part2 part3

stop:
> -gcloud app versions stop fixed1 fixed2 fixed4 thr1 --quiet
