"""Génère les figures et leurs CSV à partir des journaux bruts de raw/.
Usage (depuis la racine du dépôt) : python bench/make_figures.py
"""
import csv, os, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW, OUT = "raw/part1", "figures"
os.makedirs(OUT, exist_ok=True)

def load(*names):
    """Concatène les requêtes réussies (HTTP 200) des fichiers donnés."""
    rows = []
    for n in names:
        with open(f"{RAW}/{n}.csv") as f:
            rows += [r for r in csv.DictReader(f) if r["STATUS"] == "200"]
    return rows

def stats(rows):
    srv = sorted(float(r["SERVER_MS"]) for r in rows if r["SERVER_MS"])
    lat = sorted(float(r["LATENCY_MS"]) for r in rows)
    q = lambda x, p: statistics.quantiles(x, n=4)[p] if len(x) > 1 else x[0]
    return dict(n=len(rows), instances=len({r["INSTANCE"] for r in rows}),
                srv_med=statistics.median(srv), srv_q1=q(srv, 0), srv_q3=q(srv, 2),
                lat_med=statistics.median(lat), lat_q1=q(lat, 0), lat_q3=q(lat, 2))

def write_csv(path, header, lines):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(lines)

def errbar(ax, xs, ss, key, **kw):
    ax.errorbar(xs, [s[f"{key}_med"] for s in ss],
                yerr=[[s[f"{key}_med"] - s[f"{key}_q1"] for s in ss],
                      [s[f"{key}_q3"] - s[f"{key}_med"] for s in ss]],
                marker="o", capsize=3, **kw)

# ---------- Fig. 1a : temps serveur médian selon U et selon P ----------
serie_U = [(100, ["u100"]), (1000, ["base_debut", "base_fin"]), (10000, ["u10000"])]
serie_P = [(10, ["p10"]), (20, ["u100"]), (100, ["p100"]), (1000, ["p1000"])]
lines = []
for facteur, serie, fixes in (("U", serie_U, "P=20;F=20"), ("P", serie_P, "U=100;F=20")):
    for v, names in serie:
        s = stats(load(*names))
        lines.append([facteur, v, fixes, "+".join(names), s["n"], s["instances"],
                      round(s["srv_med"], 1), round(s["srv_q1"], 1), round(s["srv_q3"], 1)])
write_csv(f"{OUT}/fig1a.csv",
          ["facteur", "valeur", "parametres_fixes", "fichiers_raw", "n_requetes", "n_instances",
           "serveur_median_ms", "serveur_q1_ms", "serveur_q3_ms"], lines)

fig, ax = plt.subplots(figsize=(7, 4.5))
for facteur, label in (("U", "U (P = 20, F = 20)"), ("P", "P (U = 100, F = 20)")):
    pts = [l for l in lines if l[0] == facteur]
    ax.errorbar([l[1] for l in pts], [l[6] for l in pts],
                yerr=[[l[6] - l[7] for l in pts], [l[8] - l[6] for l in pts]],
                marker="o", capsize=3, label=label)
ax.set_xscale("log"); ax.set_ylim(bottom=0)
ax.set_xlabel("valeur du paramètre (échelle log)"); ax.set_ylabel("temps serveur médian (ms)")
ax.set_title("Fig. 1a — Temps serveur d'une timeline selon U et P\nfixed1, 1 requête à la fois, 60 s par jeu (barres : quartiles)")
ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f"{OUT}/fig1a.png", dpi=150)

# ---------- Fig. 1b : temps serveur et latence client médians selon F ----------
Fs = list(range(5, 101, 5))
ss = [stats(load(f"f{f:02d}")) for f in Fs]
write_csv(f"{OUT}/fig1b.csv",
          ["F", "parametres_fixes", "n_requetes", "n_instances",
           "serveur_median_ms", "serveur_q1_ms", "serveur_q3_ms",
           "client_median_ms", "client_q1_ms", "client_q3_ms", "ecart_client_serveur_ms"],
          [[f, "U=120;P=20", s["n"], s["instances"],
            round(s["srv_med"], 1), round(s["srv_q1"], 1), round(s["srv_q3"], 1),
            round(s["lat_med"], 1), round(s["lat_q1"], 1), round(s["lat_q3"], 1),
            round(s["lat_med"] - s["srv_med"], 1)] for f, s in zip(Fs, ss)])

fig, ax = plt.subplots(figsize=(7, 4.5))
errbar(ax, Fs, ss, "srv", label="temps serveur médian (Server-Timing)")
errbar(ax, Fs, ss, "lat", label="latence client médiane", alpha=.7)
ax.axvline(29.5, color="grey", ls="--")
ax.set_xlabel("F (nombre de followees)"); ax.set_ylabel("ms"); ax.set_ylim(bottom=0)
ax.text(31, ax.get_ylim()[1] * .13, "F + 1 > 30 : limite du IN dépassée,\nboucle de F + 1 requêtes", fontsize=8)
# Zoom sur F <= 25 (chemin IN), invisible à l'échelle principale
ins = ax.inset_axes([0.06, 0.45, 0.32, 0.4])
k = [i for i, f in enumerate(Fs) if f <= 25]
errbar(ins, [Fs[i] for i in k], [ss[i] for i in k], "srv")
errbar(ins, [Fs[i] for i in k], [ss[i] for i in k], "lat", alpha=.7)
ins.set_ylim(bottom=0); ins.set_title("zoom F ≤ 25 (chemin IN)", fontsize=8)
ins.tick_params(labelsize=7); ins.grid(alpha=.3)
ax.set_title("Fig. 1b — Coût d'une timeline selon F\nU = 120, P = 20, fixed1, 1 requête à la fois, 60 s par jeu (barres : quartiles)")
ax.legend(loc="lower right"); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f"{OUT}/fig1b.png", dpi=150)

print("Figures et CSV écrits dans figures/ : fig1a.png, fig1a.csv, fig1b.png, fig1b.csv")
