"""Résumé de chaque CSV Locust : requêtes, échecs, codes HTTP, instances distinctes, médianes."""
import csv, glob, statistics, sys, collections
for path in sorted(glob.glob(f"{sys.argv[1]}/*.csv")):
    rows = list(csv.DictReader(open(path)))
    ok = [r for r in rows if r["STATUS"] == "200"]
    codes = collections.Counter(r["STATUS"] for r in rows)
    inst = {r["INSTANCE"] for r in ok if r["INSTANCE"]}
    srv = [float(r["SERVER_MS"]) for r in ok if r["SERVER_MS"]]
    lat = [float(r["LATENCY_MS"]) for r in ok]
    med = lambda x: f"{statistics.median(x):8.1f}" if x else "     n/a"
    print(f"{path.split('/')[-1]:16s} n={len(rows):5d} echecs={len(rows)-len(ok):3d} codes={dict(codes)} "
          f"instances={len(inst)} serveur_med={med(srv)} ms client_med={med(lat)} ms")
