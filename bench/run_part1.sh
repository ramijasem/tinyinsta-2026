#!/usr/bin/env bash
# Partie 1 : fixed1, -u 1, 60 s par jeu, ordre mélangé (graine 42), base au début et à la fin.
set -euo pipefail
cd "$(dirname "$0")/.."
URL=$(gcloud app versions describe fixed1 --service default --format='value(versionUrl)')
DUR=${DUR:-60s}
OUT=raw/part1
mkdir -p "$OUT"

run() {  # run <nom_fichier> <prefixe> <U> <durée>
  echo "$(date -u +%FT%TZ) start $1" | tee -a "$OUT/manifest.txt"
  TINY_PREFIX=$2 TINY_USERS=$3 TINY_LOG="$OUT/$1.csv" \
    python -m locust -f bench/locustfile.py --headless -u 1 -r 1 -t "$4" --only-summary --host "$URL"
}

JEUX="u100:100 u10000:10000 p10:100 p100:100 p1000:100"
for f in $(seq 5 5 100); do JEUX="$JEUX $(printf 'f%02d' $f):120"; done
ORDRE=$(echo $JEUX | tr ' ' '\n' | shuf --random-source=<(yes 42))
{ echo "version=fixed1 url=$URL duree=$DUR"; echo base_debut; echo "$ORDRE"; echo base_fin; } > "$OUT/order.txt"

# Attendre que l'instance fixed1 soit prête (500 pendant son démarrage, observé le 13/11)
ok=0
until [ $ok -ge 10 ]; do
  if curl -s -D - -o /dev/null "$URL/api/timeline?user=base_u00000" | grep -qi "^x-instance"; then ok=$((ok+1)); else ok=0; sleep 2; fi
done
echo "$(date -u +%FT%TZ) instance prete" | tee -a "$OUT/manifest.txt"

run _chauffe base 1000 20s
run base_debut base 1000 "$DUR"
for j in $ORDRE; do run "${j%%:*}" "${j%%:*}" "${j##*:}" "$DUR"; done
run base_fin base 1000 "$DUR"
echo "TERMINE $(date -u +%FT%TZ)" | tee -a "$OUT/manifest.txt"
