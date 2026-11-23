"""Baca hasil training EADRO di work/result/ dan buat TABEL + GAMBAR.

Kode asli EADRO hanya menulis teks (running.log, experiments.txt). Skrip ini mem-parse running.log + params.json tiap run lalu membuat:
  work/result/ringkasan_hasil.csv            satu baris per run (tabel utama; termasuk fusion, kriteria pemilihan epoch, efisiensi)
  work/result/gambar/kurva_loss.png          training loss per epoch (satu panel per skema, satu warna per fusion, garis tipis = seed)
  work/result/gambar/val_hr1_std.png         HR@1(std) pada Val di epoch evaluasi (titik besar = epoch terpilih)
  work/result/gambar/hasil_akhir_<run>.png   metrik Test pada epoch terpilih: versi kode asli vs versi baku (std)
  work/result/gambar/perbandingan_fusion_<skema>.png   Test per fusion: titik = seed, penanda besar = rata-rata (bila >= 2 fusion selesai)

Pakai:  python pipeline/baca_hasil.py [--result-dir work/result] [--run <hash_id>]
Atau import dari notebook (lihat Hasil_Training.ipynb).
Catatan: bila running.log memuat beberapa percobaan (parameter identik -> hash sama -> log ditambah, bukan ditimpa), yang dibaca
hanya percobaan TERAKHIR (mulai dari "Epoch 1/"). Run lama (sebelum ada --fusion/--select_metric) dianggap fusion "concat_glu",
kriteria pemilihan epoch "HR@1" (kriteria kode asli).
"""
import argparse
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Palet kategorikal tervalidasi (5 slot pertama, mode terang) + warna chrome. Dipakai berurutan, tidak diputar.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]  # biru, oranye, aqua, kuning, magenta
GRAY = "#c3c2b7"          # de-emphasis (versi kode asli, baseline pada grafik perbandingan)
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
FUSION_ORDER = ["concat_glu", "concat_fc", "gmu", "sum", "attn", "lmf"]   # warna mengikuti entitas, bukan peringkat
FUSION_COLOR = dict(zip(FUSION_ORDER, SERIES))

RE_EPOCH = re.compile(r"Epoch (\d+)/(\d+), training loss: ([\d.]+) \[([\d.]+)s\]")
RE_EVAL = re.compile(r"INFO (Val|Test) -- (.*)$")
RE_BEST = re.compile(r"Best result got at epoch (\d+) with validation (\S+): ([\d.]+)")
RE_STOP = re.compile(r"Early stop at epoch: (\d+)")
RE_EFF = re.compile(r"Efficiency -- params_total: (\d+), params_fusion: (\d+), infer_ms_per_window: ([\d.]+), peak_rss_mb: (\d+)")


def _parse_metrics(text):
    out = {}
    for part in text.split(", "):
        k, v = part.rsplit(": ", 1)
        out[k.strip()] = float(v)
    return out


def parse_run(run_dir):
    """Dict berisi params, kurva loss, hasil evaluasi, epoch terpilih, efisiensi, status."""
    with open(os.path.join(run_dir, "params.json")) as f:
        params = json.load(f)
    epochs, evals, cur, best_epoch, stopped, finished, eff = [], [], 0, None, None, False, {}
    with open(os.path.join(run_dir, "running.log")) as f:
        for line in f:
            m = RE_EPOCH.search(line)
            if m:
                cur = int(m.group(1))
                if cur == 1 and epochs:  # percobaan baru pada log yang sama -> buang yang lama
                    epochs, evals, best_epoch, stopped, finished, eff = [], [], None, None, False, {}
                epochs.append({"epoch": cur, "loss": float(m.group(3)), "sec": float(m.group(4))})
                continue
            m = RE_EVAL.search(line)
            if m:
                evals.append({"split": m.group(1), "epoch": cur, **_parse_metrics(m.group(2))})
                continue
            m = RE_BEST.search(line)
            if m:
                best_epoch = int(m.group(1))
            m = RE_STOP.search(line)
            if m:
                stopped = int(m.group(1))
            m = RE_EFF.search(line)
            if m:
                eff = {"params_total": int(m.group(1)), "params_fusion": int(m.group(2)),
                       "ms_per_window": float(m.group(3)), "peak_rss_mb": int(m.group(4))}
            if "Current hash_id" in line:
                finished = True
    tests = [e for e in evals if e["split"] == "Test"]
    if best_epoch is None and tests:  # run 1 epoch ("Unable to convergence") tidak mencetak "Best result"
        best_epoch = tests[-1]["epoch"]
    return {"hash": os.path.basename(os.path.normpath(run_dir)), "params": params, "epochs": epochs, "evals": evals,
            "best_epoch": best_epoch, "stopped": stopped, "finished": finished, "eff": eff,
            "final_test": tests[-1] if tests else None, "mtime": os.path.getmtime(os.path.join(run_dir, "running.log"))}


def load_runs(result_dir):
    runs = []
    for d in sorted(os.listdir(result_dir)):
        p = os.path.join(result_dir, d)
        if os.path.isfile(os.path.join(p, "params.json")) and os.path.isfile(os.path.join(p, "running.log")):
            r = parse_run(p)
            if r["epochs"]:
                runs.append(r)
    return sorted(runs, key=lambda r: r["mtime"])


def scheme_of(run):
    return run["params"]["data"].split("/")[-1]


def fusion_of(run):
    return run["params"].get("fusion", "concat_glu")


def criterion_of(run):
    return run["params"].get("select_metric", "HR@1")


def _train_seconds(run):
    """Jumlah waktu epoch; epoch yang jauh lebih lama dari biasanya (>5x median, mis. laptop tidur) diganti median."""
    secs = [e["sec"] for e in run["epochs"]]
    med = float(np.median(secs))
    return sum(x if x <= 5 * med else med for x in secs)


def _sec_per_epoch(run):
    secs = [e["sec"] for e in run["epochs"]]
    med = float(np.median(secs))
    return float(np.mean([x for x in secs if x <= 5 * med]))


def summary_table(runs):
    rows = []
    for r in runs:
        p, t, eff = r["params"], r["final_test"] or {}, r["eff"]
        val = [e for e in r["evals"] if e["split"] == "Val" and e["epoch"] == r["best_epoch"]]
        n = len(r["epochs"])
        rows.append({
            "run": r["hash"], "skema": scheme_of(r), "fusion": fusion_of(r), "kriteria": criterion_of(r), "seed": p["random_seed"],
            "epoch_diminta": p["epoches"], "epoch_jalan": n,
            "status": ("selesai" if r["finished"] else "berjalan") + (" (uji cepat)" if r["finished"] and n < 10 else ""),
            "epoch_terpilih": r["best_epoch"], "menit_latih": round(_train_seconds(r) / 60, 1),
            "detik_per_epoch": round(_sec_per_epoch(r), 1),
            "params_total": eff.get("params_total", np.nan), "params_fusion": eff.get("params_fusion", np.nan),
            "ms_per_jendela": eff.get("ms_per_window", np.nan), "ram_puncak_mb": eff.get("peak_rss_mb", np.nan),
            "Val HR@1(std)": val[0]["HR@1(std)"] if val else np.nan,
            "Test F1(std)": t.get("F1(std)", np.nan), "Test HR@1(std)": t.get("HR@1(std)", np.nan),
            "Test HR@3(std)": t.get("HR@3(std)", np.nan), "Test HR@5(std)": t.get("HR@5(std)", np.nan),
            "Test ndcg@3(std)": t.get("ndcg@3(std)", np.nan), "Test ndcg@5(std)": t.get("ndcg@5(std)", np.nan),
            "Test F1": t.get("F1", np.nan), "Test HR@1": t.get("HR@1", np.nan),
            "Test HR@3": t.get("HR@3", np.nan), "Test HR@5": t.get("HR@5", np.nan),
        })
    return pd.DataFrame(rows)


def _finished(df):
    return df[(df["status"] == "selesai") & (df["epoch_jalan"] >= 10)]


def aggregate_table(df):
    """Rata-rata ± simpangan baku antar seed, per (skema, fusion, kriteria); hanya run selesai & bukan uji cepat."""
    cols = ["Val HR@1(std)", "Test F1(std)", "Test HR@1(std)", "Test HR@3(std)", "Test HR@5(std)", "Test ndcg@3(std)", "Test HR@1"]
    rows = []
    for (sk, fu, kr), g in _finished(df).groupby(["skema", "fusion", "kriteria"]):
        row = {"skema": sk, "fusion": fu, "kriteria": kr, "jumlah_seed": len(g)}
        for c in cols:
            row[c] = "{:.3f} ± {:.3f}".format(g[c].mean(), g[c].std(ddof=1)) if len(g) > 1 else "{:.3f}".format(g[c].iloc[0])
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out["_o"] = out["fusion"].map(lambda f: FUSION_ORDER.index(f) if f in FUSION_ORDER else 99)
        out = out.sort_values(["skema", "kriteria", "_o"]).drop(columns="_o")
    return out


def efficiency_table(df):
    """Efisiensi per fusion (rata-rata run selesai): jumlah parameter, waktu inferensi, waktu latih per epoch, memori puncak."""
    g = _finished(df).dropna(subset=["params_total"])
    if not len(g):
        return pd.DataFrame()
    out = g.groupby("fusion").agg(jumlah_run=("run", "count"), params_total=("params_total", "first"), params_fusion=("params_fusion", "first"),
                                  ms_per_jendela=("ms_per_jendela", "mean"), detik_per_epoch=("detik_per_epoch", "mean"),
                                  ram_puncak_mb=("ram_puncak_mb", "max")).round(3).reset_index()
    out["_o"] = out["fusion"].map(lambda f: FUSION_ORDER.index(f) if f in FUSION_ORDER else 99)
    return out.sort_values("_o").drop(columns="_o")


# ---------- gambar ----------
def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)


def _by_scheme(runs):
    schemes = sorted({scheme_of(r) for r in runs})
    return schemes, {s: [r for r in runs if scheme_of(r) == s] for s in schemes}


def _fusions(runs):
    fs = sorted({fusion_of(r) for r in runs}, key=lambda f: FUSION_ORDER.index(f) if f in FUSION_ORDER else 99)
    return fs


def _color(f, i=0):
    return FUSION_COLOR.get(f, GRAY)


def _panels(runs, ylabel, title, series_fn, path, mark_best=False, ylim=None):
    """Satu panel per skema; satu warna per fusion; garis tipis = tiap run (seed), garis tebal = rata-rata bila >= 2 run."""
    schemes, groups = _by_scheme(runs)
    fig, axes = plt.subplots(1, len(schemes), figsize=(max(7.6, 5.8 * len(schemes)), 4.2), facecolor=SURFACE, squeeze=False, sharey=True)
    for ax, sk in zip(axes[0], schemes):
        _style(ax)
        ax.set_title(sk, loc="left", fontsize=11, color=INK, fontweight="bold")
        ax.set_xlabel("epoch", color=INK2, fontsize=9)
        fus = _fusions(groups[sk])
        all_x = []
        for f in fus:
            rs = [r for r in groups[sk] if fusion_of(r) == f]
            c = _color(f)
            per_epoch = {}
            for r in rs:
                xs, ys = series_fn(r)
                if not xs:
                    continue
                all_x += xs
                multi = len(rs) > 1
                ax.plot(xs, ys, color=c, linewidth=1.0 if multi else 1.6, alpha=0.4 if multi else 1.0, solid_capstyle="round",
                        marker="o" if (mark_best or len(xs) < 4) and not multi else None, markersize=6, markeredgecolor=SURFACE, markeredgewidth=2)
                if mark_best and r["best_epoch"] in xs:
                    k = xs.index(r["best_epoch"])
                    ax.plot([xs[k]], [ys[k]], marker="o", markersize=11, color=c, alpha=0.8 if multi else 1.0,
                            markeredgecolor=SURFACE, markeredgewidth=2, zorder=5)
                for x, y in zip(xs, ys):
                    per_epoch.setdefault(x, []).append(y)
            label = f if len(rs) == 1 else "{} (rata-rata {} seed)".format(f, len(rs))
            if len(rs) > 1:
                mx = sorted(x for x, v in per_epoch.items() if len(v) >= 2)
                if mx:
                    ax.plot(mx, [np.mean(per_epoch[x]) for x in mx], color=c, linewidth=1.8, solid_capstyle="round", solid_joinstyle="round")
            ax.plot([], [], color=c, linewidth=1.8, label=label)  # entri legenda
            if len(fus) == 1 and len(rs) == 1 and per_epoch:
                x_last = max(per_epoch)
                ax.annotate(label + ("" if rs[0]["finished"] else " (berjalan)"), (x_last, per_epoch[x_last][0]), xytext=(6, 0),
                            textcoords="offset points", fontsize=8, color=INK2, va="center")
        single_pt = all_x and min(all_x) == max(all_x)
        ax.margins(x=0.12 if len(fus) == 1 and len(groups[sk]) == 1 else 0.05)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        if single_pt:  # satu titik saja: beri ruang agar sumbu-x tidak berisi pecahan
            ax.set_xlim(min(all_x) - 1, max(all_x) + 1)
            ax.set_xticks([min(all_x)])
        if len(fus) >= 2 or len(groups[sk]) >= 2:
            ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="best")
    if ylim:  # skala tetap agar variasi kecil tidak tampak seperti lonjakan besar
        axes[0][0].set_ylim(*ylim)
    axes[0][0].set_ylabel(ylabel, color=INK2, fontsize=9)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def plot_loss(runs, path):
    return _panels(runs, "training loss", "Training loss per epoch (harus cenderung turun)",
                   lambda r: ([e["epoch"] for e in r["epochs"]], [e["loss"] for e in r["epochs"]]), path)


def plot_val(runs, path):
    def fn(r):
        v = [e for e in r["evals"] if e["split"] == "Val"]
        return [e["epoch"] for e in v], [e["HR@1(std)"] for e in v]
    return _panels(runs, "HR@1(std) pada Val", "HR@1(std) pada Val (titik besar = epoch terpilih)", fn, path, mark_best=True, ylim=(0, 1))


def plot_final(run, path):
    t = run["final_test"]
    names = ["F1", "Rec", "Pre", "HR@1", "HR@3", "HR@5", "ndcg@3", "ndcg@5"]
    asli = [t[n] for n in names]
    std = [t[n + "(std)"] for n in names]
    y = np.arange(len(names))[::-1]
    h = 0.34
    fig, ax = plt.subplots(figsize=(7.2, 5.2), facecolor=SURFACE)
    _style(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.barh(y + h / 2 + 0.02, std, height=h, color=SERIES[0], label="Versi baku (std)")
    ax.barh(y - h / 2 - 0.02, asli, height=h, color=GRAY, label="Versi kode asli")
    for yy, a, s in zip(y, asli, std):
        ax.text(s + 0.01, yy + h / 2 + 0.02, "{:.3f}".format(s), va="center", fontsize=8, color=INK)
        ax.text(a + 0.01, yy - h / 2 - 0.02, "{:.3f}".format(a), va="center", fontsize=8, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(names, color=INK2, fontsize=9)
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("nilai (0–1, makin tinggi makin baik)", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    ax.set_title("Hasil Test run {} ({}, {}, seed {}, epoch terpilih {})".format(
        run["hash"], scheme_of(run), fusion_of(run), run["params"]["random_seed"], run["best_epoch"]),
        loc="left", fontsize=11, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


COMPARE_METRICS = [("Test HR@1(std)", "HR@1 (std)"), ("Test HR@3(std)", "HR@3 (std)"),
                   ("Test ndcg@3(std)", "NDCG@3 (std)"), ("Test F1(std)", "F1 deteksi (std)")]


def plot_compare(df, scheme, kriteria, path):
    """Perbandingan fusion pada satu skema: titik = tiap seed, penanda besar = rata-rata. Baseline abu-abu, varian biru (penekanan)."""
    g = _finished(df)
    g = g[(g["skema"] == scheme) & (g["kriteria"] == kriteria)]
    fus = [f for f in FUSION_ORDER if f in set(g["fusion"])] + sorted(set(g["fusion"]) - set(FUSION_ORDER))
    if len(fus) < 2:
        return None
    fig, axes = plt.subplots(1, len(COMPARE_METRICS), figsize=(3.2 * len(COMPARE_METRICS) + 1.4, 0.55 * len(fus) + 2.4), facecolor=SURFACE, sharey=True)
    y = np.arange(len(fus))[::-1]
    rng = np.random.default_rng(0)
    for ax, (col, title) in zip(axes, COMPARE_METRICS):
        _style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID, linewidth=1)
        for yy, f in zip(y, fus):
            v = g.loc[g["fusion"] == f, col].to_numpy()
            c = MUTED if f == "concat_glu" else SERIES[0]  # baseline abu-abu tua (GRAY terlalu pucat untuk titik kecil)
            ax.scatter(v, yy + rng.uniform(-0.12, 0.12, len(v)), s=28, color=c, alpha=0.6, edgecolor=SURFACE, linewidth=1, zorder=3)
            ax.scatter([v.mean()], [yy], s=95, marker="D", color=c, edgecolor=SURFACE, linewidth=2, zorder=4)
            ax.annotate("{:.3f}".format(v.mean()), (v.mean(), yy), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=7.5, color=INK2)
        ax.set_title(title, loc="left", fontsize=10, color=INK, fontweight="bold")
        ax.margins(x=0.15)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(["{} (n={})".format(f, int((g["fusion"] == f).sum())) for f in fus], color=INK2, fontsize=9)
    n_seed = int(g.groupby("fusion").size().min())
    fig.suptitle("Perbandingan fusion pada {} (kriteria epoch: {}). Titik = seed, belah ketupat = rata-rata{}".format(
        scheme, kriteria, "; hanya {} seed per fusion: selisih kecil belum berarti".format(n_seed) if n_seed < 3 else ""),
        x=0.01, ha="left", fontsize=11, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def pick_run(runs, hash_id=None):
    if hash_id:
        return next(r for r in runs if r["hash"] == hash_id)
    done = [r for r in runs if r["finished"] and r["final_test"]]
    full = [r for r in done if len(r["epochs"]) >= 10]
    return (full or done or [None])[-1]


def make_all(result_dir, hash_id=None):
    runs = load_runs(result_dir)
    if not runs:
        raise SystemExit("Belum ada run di " + result_dir)
    out = os.path.join(result_dir, "gambar")
    os.makedirs(out, exist_ok=True)
    df = summary_table(runs)
    df.to_csv(os.path.join(result_dir, "ringkasan_hasil.csv"), index=False)
    # grafik garis: run uji cepat (< 10 epoch yang sudah selesai) dikeluarkan; tetap ada di tabel
    plot_runs = [r for r in runs if not (r["finished"] and len(r["epochs"]) < 10)] or runs
    files = [plot_loss(plot_runs, os.path.join(out, "kurva_loss.png"))]
    if any(e["split"] == "Val" for r in plot_runs for e in r["evals"]):
        files.append(plot_val(plot_runs, os.path.join(out, "val_hr1_std.png")))
    r = pick_run(runs, hash_id)
    if r:
        files.append(plot_final(r, os.path.join(out, "hasil_akhir_{}.png".format(r["hash"]))))
    for (sk, kr), _ in _finished(df).groupby(["skema", "kriteria"]):
        p = plot_compare(df, sk, kr, os.path.join(out, "perbandingan_fusion_{}_{}.png".format(sk, kr.replace("(", "").replace(")", ""))))
        if p:
            files.append(p)
    return runs, df, files


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--result-dir", default=os.path.join(here, "..", "work", "result"))
    ap.add_argument("--run", default=None, help="hash_id untuk gambar hasil akhir (default: run selesai terbaru)")
    a = ap.parse_args()
    runs, df, files = make_all(os.path.abspath(a.result_dir), a.run)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(df.drop(columns=["epoch_diminta", "Test F1", "Test HR@1", "Test HR@3", "Test HR@5"]).to_string(index=False))
    agg = aggregate_table(df)
    if len(agg):
        print("\nRata-rata ± simpangan baku antar seed (run selesai, bukan uji cepat):")
        print(agg.to_string(index=False))
    eff = efficiency_table(df)
    if len(eff):
        print("\nEfisiensi per fusion:")
        print(eff.to_string(index=False))
    print("\nTabel : " + os.path.join(os.path.abspath(a.result_dir), "ringkasan_hasil.csv"))
    for f in files:
        print("Gambar: " + f)
