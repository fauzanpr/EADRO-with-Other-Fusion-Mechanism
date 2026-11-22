#!/usr/bin/env python3
"""Grafik efisiensi T: (1) kualitas melawan biaya latih, (2) biaya hasil ukur (FLOPs, latensi, aktivasi) per T.

Pakai (dari akar proyek, setelah pipeline/ukur_efisiensi.py --mode T menulis work/efisiensi_T.json):
    work/envs/train312/bin/python -I pipeline/plot_efisiensi_T.py
Hasil: Report/Gambar_Efisiensi_T.png (kualitas vs biaya) dan Report/Gambar_Ukur_T.png (hasil ukur).
Kualitas dibaca dari work/result/*/running.log lewat modul yang sama dengan pipeline/plot_kurva_T.py (concat_glu, 15 epoch).
"""
import io, contextlib, json, statistics as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    import plot_kurva_T as base   # membaca log dan membuat dua gambar lama; hasilnya identik dengan yang sudah ada
rows, plt = base.rows, base.plt
SURF, INK, INK2, GRID, C1, C2 = base.SURF, base.INK, base.INK2, base.GRID, base.C1, base.C2
Ts = {"within_event": [5, 10, 30, 40, 50, 60], "leave_event_out": [10, 30, 40, 50, 60]}
title = {"within_event": "within_event", "leave_event_out": "leave_event_out"}
get = lambda T, s, k: [r[k] for r in rows if r["data"] == base.name(T, s)]

# ---- (1) kualitas melawan biaya latih
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True, facecolor=SURF)
for ax, s in zip(axs, Ts):
    ax.set_facecolor(SURF)
    xs = [st.mean(get(T, s, "ep")) for T in Ts[s]]
    m = {k: [st.mean(get(T, s, k)) for T in Ts[s]] for k in ("F1", "HR1")}
    sd = {k: [st.stdev(get(T, s, k)) for T in Ts[s]] for k in ("F1", "HR1")}
    for k, c, mk, lab in (("F1", C1, "o", "F1"), ("HR1", C2, "s", "HR@1")):
        ax.errorbar(xs, m[k], yerr=sd[k], color=c, marker=mk, markersize=7, markeredgecolor=SURF, markeredgewidth=1.5,
                    linewidth=2, capsize=3, elinewidth=1.2, label=lab, zorder=3)
    for i, T in enumerate(Ts[s]):   # satu label T per titik: di atas titik yang lebih tinggi; bila terlalu dekat dengan titik sebelumnya (T=5), di bawah
        low = (T == 5)
        if low:
            y = min(m["F1"][i] - sd["F1"][i], m["HR1"][i] - sd["HR1"][i]) - 0.012
            ax.annotate("T=%d" % T, (xs[i], y), ha="center", va="top", fontsize=8.5, color=INK2)
        else:
            hi = max(m["F1"][i], m["HR1"][i])
            y = hi + max(sd["F1"][i], sd["HR1"][i]) + 0.012
            ax.annotate("T=%d" % T, (xs[i], y), ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.set_title(title[s], fontsize=10.5, loc="left", color=INK)
    ax.set_xlabel("Waktu latih per epoch (detik, laptop CPU)")
    ax.set_xlim(0, 345); ax.set_ylim(0.4, 1.05)
    ax.grid(axis="y", color=GRID, linewidth=.8); ax.set_axisbelow(True)
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(length=0)
axs[0].set_ylabel("Test, metrik std (rata-rata ± sd, 3 seed)")
axs[0].legend(loc="lower right", frameon=False, fontsize=9.5, labelcolor=INK2)
fig.suptitle("Kualitas melawan biaya latih per epoch, tiap titik satu T", x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=INK)
fig.text(0.01, 0.005, "Tiap titik = satu T (label di atas titik). Batang = ± sd (n−1), 3 seed. Latensi deteksi = T detik (jendela harus terkumpul dulu).", fontsize=8.5, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 0.93))
fig.savefig("Report/Gambar_Efisiensi_T.png", dpi=160, facecolor=SURF)

# ---- (2) hasil ukur tanpa data (pipeline/ukur_efisiensi.py)
J = json.load(open("work/efisiensi_T.json"))
R = {r["T"]: r for r in J["rows"]}
T_ = sorted(R)
th = J["threads"]
fig, axs = plt.subplots(1, 4, figsize=(13, 3.6), facecolor=SURF)
spec = [
    ("FLOPs per jendela (juta)", [("flops", "total", C1, "o"), ("flops_temporal", "cabang trace+metric", C2, "s")], 1e6),
    ("Latensi satu jendela (ms, median)", [("lat_b1_ms_t%d" % th, "%d thread" % th, C1, "o"), ("lat_b1_ms_t1", "1 thread", C2, "s")], 1),
    ("Waktu latih per jendela (ms)", [("train_ms_per_window", "forward+backward+Adam", C1, "o")], 1),
    ("Elemen aktivasi per jendela (ribu)", [("act_elems", "keluaran modul", C1, "o")], 1e3),
]
for ax, (t, series, div) in zip(axs, spec):
    ax.set_facecolor(SURF)
    for k, lab, c, mk in series:
        ys = [R[T][k] / div for T in T_]
        ax.plot(T_, ys, color=c, marker=mk, markersize=6, markeredgecolor=SURF, markeredgewidth=1.2, linewidth=2, label=lab)
        dy = {"1 thread": -7}.get(lab, 7 if len(series) > 1 else 0)
        txt = ("%.1f" % ys[-1]) if ys[-1] < 100 else "%.0f" % ys[-1]
        ax.annotate(txt, (T_[-1], ys[-1]), xytext=(6, dy), textcoords="offset points", va="center", fontsize=8.5, color=INK2)
    ax.set_title(t, fontsize=9.5, loc="left", color=INK); ax.set_xlabel("T (detik)")
    ax.set_xticks(T_); ax.set_xlim(2, 68); ax.set_ylim(bottom=0)
    ax.grid(axis="y", color=GRID, linewidth=.8); ax.set_axisbelow(True)
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(length=0)
    if len(series) > 1: ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=INK2)
fig.suptitle("Biaya hasil ukur (data acak berbentuk sama, median 3 ronde, laptop CPU)", x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.92))
fig.savefig("Report/Gambar_Ukur_T.png", dpi=160, facecolor=SURF)
print("ok")
