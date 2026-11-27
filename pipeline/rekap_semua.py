#!/usr/bin/env python3
"""Rekap SELURUH eksperimen: nilai per seed, rata-rata ± sd, dan selisih terhadap baseline (Welch, CI 95%).

Pakai (dari akar proyek):
    work/envs/train312/bin/python -I pipeline/rekap_semua.py            # cetak tabel Markdown
    work/envs/train312/bin/python -I pipeline/rekap_semua.py --gambar   # sekaligus Report/Gambar_Seed_Semua.png

Satu eksperimen = (data, skema, fusion, jumlah epoch, kriteria pilih epoch). Nilai = metrik Test (std) pada epoch yang
dipilih lewat Val (baris "Best result got at epoch"), sama dengan pipeline/rekap_seed.py.
Selisih dianggap terbukti hanya bila CI 95% Welch tidak memuat 0.
"""
import glob, json, math, os, re, statistics as st, sys
from scipy import stats as sps

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "work", "result")
SEEDS = [42, 7, 123, 31, 2026]
MET = [("F1(std)", "F1"), ("Pre(std)", "Pre"), ("Rec(std)", "Rec"), ("HR@1(std)", "HR@1"), ("HR@3(std)", "HR@3")]


def parse(s):
    return {k: float(v) for k, v in re.findall(r"([A-Za-z0-9@()_]+): ([0-9.]+)", s.split(" -- ", 1)[1])}


def load():
    runs = []
    for d in sorted(glob.glob(os.path.join(RES, "*/params.json"))):
        P = json.load(open(d))
        if P.get("epoches", 0) < 5:
            continue
        L = open(os.path.join(os.path.dirname(d), "running.log")).read().splitlines()
        s = [i for i, l in enumerate(L) if "Using CPU" in l or "Using GPU" in l]
        L = L[s[-1]:] if s else L
        ep, tests, secs = 0, {}, []
        for l in L:
            m = re.search(r"Epoch (\d+)/\d+, training loss: [0-9.]+ \[([0-9.]+)s\]", l)
            if m:
                ep = int(m.group(1)); secs.append(float(m.group(2)))
            if " Test -- " in l:
                tests[ep] = parse(l)
        b = re.findall(r"Best result got at epoch (\d+) with validation (\S+): ([0-9.]+)", "\n".join(L))
        if not b or int(b[-1][0]) not in tests:
            continue
        data, scheme = P["data"].split("/")
        runs.append(dict(hash=os.path.basename(os.path.dirname(d)), T=10 if data == "A1" else int(data.split("_T")[1]),
                         scheme=scheme, fusion=P.get("fusion", "concat_glu"), epochs=P["epoches"],
                         sel=P.get("select_metric", "HR@1"), seed=P["random_seed"], ep=int(b[-1][0]),
                         t=tests[int(b[-1][0])], sec=st.mean(secs) if secs else float("nan")))
    return runs


def key(r):
    return (r["scheme"], r["epochs"], r["sel"], r["T"], r["fusion"])


def welch(a, b):
    """selisih rata-rata b - a, CI 95%"""
    na, nb = len(a), len(b)
    va, vb = st.variance(a), st.variance(b)
    se = math.sqrt(va / na + vb / nb)
    df = se ** 4 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    t = sps.t.ppf(0.975, df)
    d = st.mean(b) - st.mean(a)
    return d, d - t * se, d + t * se


def name(k):
    scheme, epochs, sel, T, fusion = k
    return "T=%d %s" % (T, {"concat_glu": "F1", "concat_fc": "F2", "gmu": "F3", "concat_glu_wide": "F1w"}.get(fusion, fusion))


def main():
    runs = load()
    groups = {}
    for r in runs:
        groups.setdefault(key(r), []).append(r)
    FORD = {"concat_glu": 0, "concat_fc": 1, "gmu": 2}
    order = lambda k: (k[0], k[1] != 15, k[3], FORD.get(k[4], 9))
    keys = sorted((k for k in groups if len(groups[k]) >= 2), key=order)   # run tunggal (n = 1, uji awal) tidak diikutkan
    out = []
    P = out.append
    for scheme in ("within_event", "leave_event_out", "random_original"):
        ks = [k for k in keys if k[0] == scheme]
        if not ks:
            continue
        P("\n### %s\n" % scheme)
        for m, lab in (("F1(std)", "F1(std)"), ("HR@1(std)", "HR@1(std)")):
            P("**%s per seed** (epoch terpilih dalam kurung)\n" % lab)
            P("| Eksperimen | n | " + " | ".join("seed %d" % s for s in SEEDS) + " | rata-rata ± sd | min – maks |")
            P("|---|---|" + "---|" * (len(SEEDS) + 2))
            for k in ks:
                by = {r["seed"]: r for r in groups[k]}
                cells = ["%.3f (%d)" % (by[s]["t"][m], by[s]["ep"]) if s in by else "–" for s in SEEDS]
                xs = [r["t"][m] for r in groups[k]]
                sd = "%.3f ± %.3f" % (st.mean(xs), st.stdev(xs)) if len(xs) > 1 else "%.3f" % xs[0]
                nm = name(k) + (" (%d ep, pilih %s)" % (k[1], k[2]) if k[1] != 15 else "")
                P("| %s | %d | %s | %s | %.3f – %.3f |" % (nm, len(xs), " | ".join(cells), sd, min(xs), max(xs)))
            P("")
        P("**Rata-rata ± sd, semua ukuran (Test, std)**\n")
        P("| Eksperimen | n | " + " | ".join(l for _, l in MET) + " | s/epoch |")
        P("|---|---|" + "---|" * (len(MET) + 1))
        for k in ks:
            g = groups[k]
            cells = []
            for m, _ in MET:
                xs = [r["t"][m] for r in g]
                cells.append("%.3f ± %.3f" % (st.mean(xs), st.stdev(xs)) if len(xs) > 1 else "%.3f" % xs[0])
            nm = name(k) + (" (%d ep)" % k[1] if k[1] != 15 else "")
            P("| %s | %d | %s | %.0f |" % (nm, len(g), " | ".join(cells), st.mean(r["sec"] for r in g)))
        P("")
        base = next((k for k in ks if k[1] == 15 and k[3] == 10 and k[4] == "concat_glu"), None)
        if base and scheme != "random_original":
            P("**Selisih terhadap baseline T=10 F1** (rata-rata eksperimen − rata-rata baseline, CI 95% Welch; **tebal** = CI tidak memuat 0)\n")
            P("| Eksperimen | n | ΔF1(std) | CI 95% | ΔHR@1(std) | CI 95% |")
            P("|---|---|---|---|---|---|")
            for k in ks:
                if k == base or k[1] != 15:
                    continue
                cells = []
                for m in ("F1(std)", "HR@1(std)"):
                    d, lo, hi = welch([r["t"][m] for r in groups[base]], [r["t"][m] for r in groups[k]])
                    b = "**" if (lo > 0 or hi < 0) else ""
                    cells += ["%s%+.3f%s" % (b, d, b), "%+.3f s.d. %+.3f" % (lo, hi)]
                P("| %s | %d | %s |" % (name(k), len(groups[k]), " | ".join(cells)))
            P("")
    print("\n".join(out))

    if "--gambar" in sys.argv:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            import plot_kurva_T as base_mod
        plt, SURF, INK, INK2, GRID, C1, C2 = (base_mod.plt, base_mod.SURF, base_mod.INK, base_mod.INK2, base_mod.GRID,
                                             base_mod.C1, base_mod.C2)
        C3 = "#1baf7a"   # aqua, sama dengan warna gmu di baca_hasil.py
        fig, axs = plt.subplots(2, 2, figsize=(12, 7.2), facecolor=SURF)
        for i, m in enumerate(("F1(std)", "HR@1(std)")):
            for j, scheme in enumerate(("within_event", "leave_event_out")):
                ax = axs[i][j]
                ax.set_facecolor(SURF)
                ks = [k for k in keys if k[0] == scheme and k[1] == 15]
                labels = []
                for x, k in enumerate(ks):
                    xs = [r["t"][m] for r in groups[k]]
                    col = {"concat_glu": C1, "concat_fc": C2, "gmu": C3}.get(k[4], INK2)
                    jit = [(-0.18 + 0.36 * n / max(1, len(xs) - 1)) if len(xs) > 1 else 0 for n in range(len(xs))]
                    ax.scatter([x + q for q in jit], xs, s=34, color=col, edgecolor=SURF, linewidth=1, zorder=3)
                    ax.hlines(st.mean(xs), x - 0.3, x + 0.3, color=INK, linewidth=2, zorder=4)
                    labels.append("%s\nn=%d" % (name(k).replace("T=", "T"), len(xs)))
                ax.set_xticks(range(len(ks))); ax.set_xticklabels(labels, fontsize=8)
                ax.set_ylim(0.3 if m.startswith("HR") else 0.6, 1.0)
                ax.set_title("%s, %s" % (m, scheme), loc="left", fontsize=10.5, color=INK)
                ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
                for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
                ax.spines["bottom"].set_color(GRID); ax.tick_params(length=0)
        fig.suptitle("Semua eksperimen, nilai per seed (titik) dan rata-rata (garis hitam)", x=0.01, ha="left",
                     fontsize=12.5, fontweight="bold", color=INK)
        fig.text(0.01, 0.005, "Biru = F1 (concat_glu), oranye = F2 (concat_fc), hijau = F3 (gmu). Test (std), epoch terpilih lewat Val. n = jumlah seed. random_original tidak ikut (protokol berbeda).",
                 fontsize=8.5, color=INK2)
        fig.tight_layout(rect=(0, 0.03, 1, 0.95))
        fig.savefig(os.path.join(ROOT, "Report", "Gambar_Seed_Semua.png"), dpi=160, facecolor=SURF)


if __name__ == "__main__":
    main()
