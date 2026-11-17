"""Génère les figures et leurs CSV à partir des journaux bruts de raw/.
Usage (depuis la racine du dépôt) : python bench/make_figures.py
"""
import csv, os, statistics, collections, glob, datetime
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
ax.legend(loc="upper center", bbox_to_anchor=(0.62, 1.0), fontsize=8); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f"{OUT}/fig1b.png", dpi=150)

print("Figures et CSV écrits dans figures/ : fig1a.png, fig1a.csv, fig1b.png, fig1b.csv")

# =====================================================================
# Partie 2 : capacité (fixed1, fixed2, fixed4 ; jeu base ; C = 1..64)
# Débit = réponses 200 dont la requête part dans la fenêtre stable [t0 + 5 s, t0 + 55 s], divisées par 50 s.
# =====================================================================
RAW2, CS, NS = "raw/part2", [1, 2, 4, 8, 16, 32, 64], [1, 2, 4]
W0, W1 = 5.0, 55.0

def stats2(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    t0 = min(float(r["T_START"]) for r in rows)
    win = [r for r in rows if W0 <= float(r["T_START"]) - t0 < W1]
    ok = [r for r in win if r["STATUS"] == "200"]
    lat = [float(r["LATENCY_MS"]) for r in ok]
    par_inst = collections.Counter(r["INSTANCE"] for r in ok)
    return dict(n=len(win), echecs=len(win) - len(ok), debit=len(ok) / (W1 - W0),
                lat_med=statistics.median(lat), lat_moy=statistics.mean(lat),
                instances=len(par_inst),
                part_max=max(par_inst.values()) / len(ok) if ok else 0)

res2 = {n: {c: stats2(f"{RAW2}/n{n}/c{c:02d}.csv") for c in CS} for n in NS}
lignes = []
for n in NS:
    for c in CS:
        s = res2[n][c]
        lignes.append([n, c, "base;U=1000;P=20;F=20", s["n"], s["echecs"], s["instances"],
                       round(s["part_max"] * 100, 1), round(s["debit"], 2),
                       round(s["lat_med"], 1), round(s["lat_moy"], 1),
                       round(c / s["debit"] * 1000, 1)])
entete = ["N_instances", "C_utilisateurs", "jeu", "n_requetes_fenetre", "n_echecs", "n_instances_vues",
          "part_instance_la_plus_chargee_pct", "debit_req_par_s", "latence_mediane_ms",
          "latence_moyenne_ms", "little_C_sur_debit_ms"]
write_csv(f"{OUT}/fig2a.csv", entete, lignes)
write_csv(f"{OUT}/fig2b.csv", entete, lignes)

fig, ax = plt.subplots(figsize=(7, 4.5))
for n in NS:
    ax.plot(CS, [res2[n][c]["debit"] for c in CS], marker="o", label=f"N = {n}")
ax.set_xscale("log", base=2); ax.set_xticks(CS); ax.set_xticklabels(CS); ax.set_ylim(bottom=0)
ax.set_xlabel("C (utilisateurs Locust simultanés, échelle log)"); ax.set_ylabel("débit (timelines servies / s)")
ax.set_title("Fig. 2a — Débit selon la concurrence, par nombre d'instances\njeu base, fixedN, 60 s par point (fenêtre stable de 50 s)")
ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(f"{OUT}/fig2a.png", dpi=150)

fig, ax = plt.subplots(figsize=(7, 4.5))
for i, n in enumerate(NS):
    col = f"C{i}"
    ax.plot(CS, [res2[n][c]["lat_med"] for c in CS], marker="o", color=col, label=f"N = {n} : latence médiane mesurée")
    ax.plot(CS, [c / res2[n][c]["debit"] * 1000 for c in CS], ls="--", color=col, label=f"N = {n} : Little, C / débit")
ax.set_xscale("log", base=2); ax.set_yscale("log"); ax.set_xticks(CS); ax.set_xticklabels(CS)
ax.set_xlabel("C (utilisateurs Locust simultanés, échelle log)"); ax.set_ylabel("latence (ms, échelle log)")
ax.set_title("Fig. 2b — Latence selon la concurrence et prédiction de la loi de Little\njeu base, fixedN, 60 s par point (fenêtre stable de 50 s)")
ax.legend(fontsize=7); ax.grid(alpha=.3, which="both"); fig.tight_layout(); fig.savefig(f"{OUT}/fig2b.png", dpi=150)

print("Partie 2 :")
for l in lignes:
    print(f"  N={l[0]} C={l[1]:2d} debit={l[7]:6.1f}/s lat_med={l[8]:7.1f} ms lat_moy={l[9]:7.1f} ms "
          f"Little={l[10]:7.1f} ms instances={l[5]} part_max={l[6]:5.1f}% echecs={l[4]}")
print("Figures et CSV écrits dans figures/ : fig2a.png, fig2a.csv, fig2b.png, fig2b.csv")

# =====================================================================
# Partie 3 : avant / après (même protocole que la Partie 2, N = 1)
# avant = fixed1 (1 worker synchrone) ; après = thr1 (gunicorn --threads 8), 2 runs identiques
# =====================================================================
RUNS3 = [("thr1_run1", "raw/part3/n1_run1"), ("thr1_run2", "raw/part3/n1_run2")]
if all(os.path.isdir(d) for _, d in RUNS3):
    def serie_temps(d, pas=10):
        rows = []
        for p in glob.glob(f"{d}/*.csv"):
            if p.endswith("request_log_appengine.csv"):
                continue
            with open(p) as f:
                rows += [r for r in csv.DictReader(f) if r["STATUS"] == "200"]
        rows.sort(key=lambda r: float(r["T_START"]))
        t0 = float(rows[0]["T_START"])
        b = collections.defaultdict(list)
        for r in rows:
            b[int((float(r["T_START"]) - t0) // pas)].append(r)
        out = [(k * pas, len(v) / pas, sum(float(r["SERVER_MS"]) for r in v) / (pas * 10), v[0]["USERS"])
               for k, v in sorted(b.items())]
        return t0, out

    avant = {c: stats2(f"raw/part2/n1/c{c:02d}.csv") for c in CS}
    apres = {nom: {c: stats2(f"{d}/c{c:02d}.csv") for c in CS} for nom, d in RUNS3}
    lignes3 = []
    for nom, res in [("avant_fixed1_1worker", avant)] + list(apres.items()):
        for c in CS:
            s = res[c]
            lignes3.append([nom, 1, c, s["n"], s["echecs"], s["instances"], round(s["debit"], 2),
                            round(s["lat_med"], 1), round(s["lat_moy"], 1), round(c / s["debit"] * 1000, 1)])
    write_csv(f"{OUT}/fig3.csv",
              ["version", "N_instances", "C_utilisateurs", "n_requetes_fenetre", "n_echecs", "n_instances_vues",
               "debit_req_par_s", "latence_mediane_ms", "latence_moyenne_ms", "little_C_sur_debit_ms"], lignes3)

    temps = {nom: serie_temps(d) for nom, d in RUNS3}
    write_csv(f"{OUT}/fig3_temps.csv", ["run", "t_s", "debit_req_par_s", "occupation_get_timeline_pct", "C_utilisateurs"],
              [[nom, t, round(x, 1), round(o), c] for nom, (_, s) in temps.items() for t, x, o, c in s])

    # pendingTime App Engine (run 1), aligné sur le début de la charge côté client
    pend = []
    lp = "raw/part3/n1_run1/request_log_appengine.csv"
    if os.path.exists(lp):
        sec = lambda s: float(s.rstrip("s")) * 1000 if s else 0.0
        t0c = temps["thr1_run1"][0]
        b = collections.defaultdict(list)
        with open(lp) as f:
            for d, lat, p in csv.reader(f):
                ts = datetime.datetime.fromisoformat(d.replace("Z", "+00:00")).timestamp()
                if ts >= t0c:
                    b[int((ts - t0c) // 10)].append(sec(p))
        pend = [(k * 10, statistics.median(v)) for k, v in sorted(b.items())]
        write_csv(f"{OUT}/fig3_pending.csv", ["t_s", "pending_median_ms"], [[t, round(p, 1)] for t, p in pend])

    fig, axs = plt.subplots(1, 3 if pend else 2, figsize=(15 if pend else 11, 4.5))
    a1, a2 = axs[0], axs[1]
    a1.plot(CS, [avant[c]["debit"] for c in CS], marker="o", color="C0", label="avant : 1 worker (fixed1)")
    for (nom, res), col in zip(apres.items(), ("C1", "C3")):
        a1.plot(CS, [res[c]["debit"] for c in CS], marker="o", color=col, label=f"après : --threads 8 ({nom})")
    a1.set_xscale("log", base=2); a1.set_xticks(CS); a1.set_xticklabels(CS); a1.set_ylim(bottom=0)
    a1.set_xlabel("C (utilisateurs simultanés, échelle log)"); a1.set_ylabel("débit (timelines / s)")
    a1.set_title("(a) débit selon C (fenêtre 5-55 s de chaque run)", fontsize=9); a1.legend(fontsize=7); a1.grid(alpha=.3)
    for (nom, (_, s)), col in zip(temps.items(), ("C1", "C3")):
        s = [x for x in s if x[0] <= 240]
        a2.plot([x[0] for x in s], [x[1] for x in s], marker=".", color=col, label=nom)
    a2.axhline(statistics.median(avant[c]["debit"] for c in CS if c >= 2), color="C0", ls="--", label="plafond fixed1")
    a2.set_xlabel("temps depuis le début de la charge (s)"); a2.set_ylabel("débit (timelines / s, tranches de 10 s)")
    a2.set_title("(b) débit dans le temps : bascule vers t ≈ 50 s", fontsize=9); a2.legend(fontsize=7); a2.grid(alpha=.3)
    if pend:
        a3 = axs[2]; p = [x for x in pend if x[0] <= 240]
        a3.plot([x[0] for x in p], [x[1] for x in p], marker=".", color="C1")
        a3.set_xlabel("temps depuis le début de la charge (s)"); a3.set_ylabel("pendingTime médian App Engine (ms)")
        a3.set_title("(c) attente dans la file d'App Engine (thr1_run1)", fontsize=9); a3.grid(alpha=.3)
    fig.suptitle("Fig. 3 — Avant / après : gunicorn --threads 8, jeu base, N = 1 instance B1, même protocole que la Partie 2")
    fig.tight_layout(); fig.savefig(f"{OUT}/fig3.png", dpi=150)
    print("Partie 3 :")
    for l in lignes3:
        print(f"  {l[0]:22s} C={l[2]:2d} debit={l[6]:6.1f}/s lat_med={l[7]:7.1f} ms lat_moy={l[8]:7.1f} ms echecs={l[4]}")
    print("Figure et CSV écrits dans figures/ : fig3.png, fig3.csv, fig3_temps.csv" + (", fig3_pending.csv" if pend else ""))
