#!/usr/bin/env bash
# Partie 3 : comme deploy_fixed.sh, mais gunicorn est lancé avec --threads 8.
# Déploie une version à N instances fixes (manual scaling), sans lui envoyer le trafic par défaut.
#
#   ./deploy_threads.sh 1      -> version "thr1", URL https://fixed1-dot-<PROJET>.<REGION>.r.appspot.com
#   ./deploy_threads.sh 4      -> version "thr4"
#   ./deploy_threads.sh 2 --project mon-projet   (arguments supplémentaires passés à gcloud)
#
# ATTENTION : une instance en manual scaling est facturée tant que la version tourne.
# Arrêtez-la dès la fin des mesures :  gcloud app versions stop thr<N>
set -euo pipefail
N="${1:?usage: ./deploy_threads.sh N [arguments gcloud]}"
shift
cd "$(dirname "$0")"
YAML="app-thr-${N}.yaml"
trap 'rm -f "$YAML"' EXIT
cat > "$YAML" <<EOF
runtime: python312
entrypoint: gunicorn -b :\$PORT --threads 8 main:app

# Manual scaling : exactement ${N} instance(s), pas d'autoscaling.
# B1 a le même CPU et la même mémoire que F1.
instance_class: B1
manual_scaling:
  instances: ${N}

handlers:
- url: /
  script: auto
env_variables:
  SEED_TOKEN: "change-me-seed-token"
EOF
gcloud app deploy "$YAML" --version "thr${N}" --no-promote --quiet "$@"
