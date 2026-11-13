#!/usr/bin/env bash
# Partie 2 : capacité. Usage : bench/run_part2.sh N   (N = 1, 2 ou 4)
# Déploie fixedN, attend qu'elle réponde, chauffe 30 s, mesure C = 1..64 (ordre mélangé),
# répète le premier C à la fin (dérive), puis ARRÊTE fixedN (même en cas d'erreur).
set -euo pipefail
cd "$(dirname "$0")/.."
N=${1:?usage: bench/run_part2.sh N}
DUR=${DUR:-60s}
OUT=raw/part2/n$N
mkdir -p "$OUT"
trap 'echo "$(date -u +%FT%TZ) arret fixed$N" | tee -a "$OUT/manifest.txt"; gcloud app versions stop "fixed$N" --quiet' EXIT

# Repartir d'une version neuve : redéployer par-dessus une version STOPPED bloque (observé le 13/11)
if gcloud app versions describe "fixed$N" --service default >/dev/null 2>&1; then
  gcloud app versions delete "fixed$N" --service default --quiet
fi
./deploy_fixed.sh "$N"
URL=$(gcloud app versions describe "fixed$N" --service default --format='value(versionUrl)')
ok=0
until [ $ok -ge 10 ]; do
  if curl -s -D - -o /dev/null "$URL/api/timeline?user=base_u00000" | grep -qi "^x-instance"; then ok=$((ok+1)); else ok=0; sleep 2; fi
done
echo "$(date -u +%FT%TZ) prete url=$URL" | tee -a "$OUT/manifest.txt"

run() {  # run <nom_fichier> <C> <durée>
  echo "$(date -u +%FT%TZ) start $1 C=$2" | tee -a "$OUT/manifest.txt"
  TINY_PREFIX=base TINY_USERS=1000 TINY_LOG="$OUT/$1.csv" \
    python -m locust -f bench/locustfile.py --headless -u "$2" -r "$2" -t "$3" --only-summary --host "$URL" \
    || echo "$(date -u +%FT%TZ) locust code $? : echecs presents (voir CSV)" | tee -a "$OUT/manifest.txt"
}

run _chauffe 16 30s
python - "$OUT/_chauffe.csv" "$N" <<'PY' | tee -a "$OUT/manifest.txt"
import csv, sys
inst = {r["INSTANCE"] for r in csv.DictReader(open(sys.argv[1])) if r["STATUS"] == "200"}
print(f"chauffe : {len(inst)} instance(s) distincte(s) pour {sys.argv[2]} attendue(s)")
PY

ORDRE=$(printf '%s\n' 1 2 4 8 16 32 64 | shuf --random-source=<(yes "42$N"))
echo $ORDRE > "$OUT/order.txt"
for c in $ORDRE; do run "c$(printf '%02d' "$c")" "$c" "$DUR"; done
first=$(echo "$ORDRE" | head -1)
run "c$(printf '%02d' "$first")_fin" "$first" "$DUR"
echo "TERMINE $(date -u +%FT%TZ)" | tee -a "$OUT/manifest.txt"
