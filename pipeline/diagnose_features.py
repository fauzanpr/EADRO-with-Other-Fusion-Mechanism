"""Langkah 2 diagnosis: kenapa model memberi alarm pada jendela normal? (hanya membaca, tidak mengubah data/model)

Bagian A  Profil metrics MENTAH di sekitar gangguan (service biang). Baseline robust (median/MAD) per run per service.
          Pertanyaan: apakah efek gangguan mulai SEBELUM label, atau berlanjut SESUDAH label berakhir (pemulihan)?
Bagian B  Apakah "jenis run" (berfault / tanpa fault) bisa ditebak dari fitur jendela NORMAL? Perbandingan tiga kelompok:
            NF  = jendela normal di run tanpa fault
            GAP = jendela normal di run berfault (celah antar-gangguan)
            FLT = jendela bergangguan
          - fitur yang paling berbeda antara NF dan GAP (metrics / aktivitas log / aktivitas trace)
          - AUC classifier logistic (leave-run-group-out) NF vs GAP, GAP vs FLT, NF vs FLT, dengan set fitur berbeda
          - pergeseran fitur antara separuh awal dan 40% akhir run tanpa fault
Bagian C  Alarm palsu per 200 detik di run tanpa fault (dari diagnosis_alarm.csv hasil diagnose_alarm.py)

Pakai:  work/envs/train312/bin/python -I pipeline/diagnose_features.py --run 9df622b8 [--parts A,B,C]
"""
import argparse
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from common import Info  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, help="hash_id run within_event yang sudah didiagnosis (diagnosis_alarm.csv)")
ap.add_argument("--scheme", default="within_event")
ap.add_argument("--parts", default="A,B,C")
ap.add_argument("--result-dir", default=os.path.join(ROOT, "work", "result"))
a = ap.parse_args()
parts = set(a.parts.split(","))

parsed = os.path.join(ROOT, "work", "preprocess", "parsed_data", "A1")
data_dir = os.path.join(ROOT, "work", "chunks", "A1", a.scheme)
info = Info("trainticket")
M = list(info.metric_names)
SV = [s[len("ts-"):-len("-service")] for s in info.service_names]
manifest = {m["idx"]: m for m in json.load(open(os.path.join(parsed, "manifest.json")))}
records = {i: json.load(open(os.path.join(parsed, "records{}.json".format(i)))) for i in manifest}
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)


def rscale(x):
    """Skala robust: 1,4826*MAD, dengan batas bawah agar kanal hampir-konstan tidak meledak."""
    mad = 1.4826 * np.median(np.abs(x - np.median(x)))
    return max(mad, 0.1 * np.std(x), 1e-12)


# ---------------------------------------------------------------- A
if "A" in parts:
    print("=" * 100 + "\nA. Profil metrics mentah service biang di sekitar gangguan (median |z-robust| antar kejadian)\n" + "=" * 100)
    durations = {}
    prof = {}  # (type, channel, 'start'/'end', bin) -> list nilai per kejadian
    ctrl = {}  # kontrol: service lain (bukan biang) pada offset yang sama
    S_BINS = [(-120, -60), (-60, -20), (-20, 0), (0, 10), (10, 30), (30, 100)]
    E_BINS = [(-30, 0), (1, 10), (11, 30), (31, 60), (61, 120)]
    for idx, m in manifest.items():
        if m["kind"] != "fault":
            continue
        raw = {}
        for s in info.service_names:
            df = pd.read_csv(os.path.join(parsed, "metrics{}".format(idx), s + ".csv")).set_index("timestamp")
            raw[s] = (df[M] - df[M].median()) / pd.Series({c: rscale(df[c].to_numpy()) for c in M})
        for fl in records[idx]["faults"]:
            durations.setdefault(fl["type"], []).append(fl["e"] - fl["s"] + 1)
            others = [s for s in info.service_names if s != fl["service"]]
            for kind, ref, bins in (("start", fl["s"], S_BINS), ("end", fl["e"], E_BINS)):
                for lo, hi in bins:
                    ts = [t for t in range(ref + lo, ref + hi + 1) if t in raw[fl["service"]].index]
                    if not ts:
                        continue
                    for c in M:
                        prof.setdefault((fl["type"], c, kind, (lo, hi)), []).append(raw[fl["service"]].loc[ts, c].abs().median())
                    ctrl.setdefault((fl["type"], kind, (lo, hi)), []).append(
                        float(np.median([raw[o].loc[ts, c].abs().median() for o in others[::4] for c in M])))
    print("Durasi gangguan (detik) per jenis: " + ", ".join("{} min/med/maks = {}/{:.0f}/{}".format(t, min(v), np.median(v), max(v)) for t, v in durations.items()))
    print("Kontrol = median |z-robust| semua service lain pada offset yang sama (nilai wajar tanpa efek sekitar 0,7)\n")
    for typ in sorted(durations):
        score = {c: np.median(prof[(typ, c, "start", (10, 30))]) for c in M}
        top = sorted(score, key=score.get, reverse=True)[:3]
        print("--- {} (jumlah kejadian {}) — 3 kanal paling responsif: {}".format(typ, len(durations[typ]), top))
        for kind, bins, title in (("start", S_BINS, "offset terhadap AWAL gangguan (detik; 0 = awal label)"),
                                  ("end", E_BINS, "offset terhadap AKHIR gangguan (detik; 0 = akhir label)")):
            rows = {c: [np.median(prof[(typ, c, kind, b)]) for b in bins] for c in top}
            rows["kontrol"] = [np.median(ctrl[(typ, kind, b)]) for b in bins]
            print(title)
            print(pd.DataFrame(rows, index=["{}..{}".format(*b) for b in bins]).T.round(2).to_string())
        print()

# ---------------------------------------------------------------- B, C membutuhkan chunk dan/atau diagnosis
if "B" in parts:
    print("=" * 100 + "\nB. Apakah jenis run bisa ditebak dari fitur jendela normal?\n" + "=" * 100)
    feats, meta_rows = [], []
    names = ["m:{}:{}".format(sv, c) for sv in SV for c in M] + ["trace:" + sv for sv in SV] + ["log:" + sv for sv in SV]
    for split in ("train", "val", "test"):
        with open(os.path.join(data_dir, "chunk_{}.pkl".format(split)), "rb") as f:
            ch = pickle.load(f)
        for k, v in ch.items():
            feats.append(np.concatenate([v["metrics"].mean(axis=1).ravel(),          # [27*7]
                                         (v["traces"][..., 0] > 0).mean(axis=1),     # fraksi detik berisi trace, [27]
                                         (np.abs(v["logs"]).sum(axis=1) > 0).astype(np.float32)]))  # log aktif, [27]
            meta_rows.append((split, v["run"], v["start"], v["culprit"]))
        del ch
    X = np.asarray(feats, dtype=np.float32)
    meta = pd.DataFrame(meta_rows, columns=["split", "run", "start", "culprit"])
    meta["kind"] = meta["run"].map(lambda r: manifest[r]["kind"])
    meta["grp"] = np.where(meta["kind"] == "no_fault", "NF", np.where(meta["culprit"] >= 0, "FLT", "GAP"))
    print("jumlah jendela: " + meta["grp"].value_counts().to_dict().__repr__())
    is_m = np.array([n.startswith("m:") for n in names])
    is_act = ~is_m

    def top_diff(g1, g2, k=10):
        a_, b_ = X[(meta["grp"] == g1).to_numpy()], X[(meta["grp"] == g2).to_numpy()]
        sd = np.sqrt((a_.var(axis=0) + b_.var(axis=0)) / 2) + 1e-9
        d = (b_.mean(axis=0) - a_.mean(axis=0)) / sd
        o = np.argsort(-np.abs(d))[:k]
        return pd.DataFrame({"fitur": [names[i] for i in o], "d (std)": d[o].round(2), "rata2 " + g1: a_.mean(axis=0)[o].round(3),
                             "rata2 " + g2: b_.mean(axis=0)[o].round(3)})

    print("\nFitur paling berbeda NF vs GAP (d = selisih rata-rata / simpangan baku gabungan; 'm' = metrics z-score, trace/log = aktivitas):")
    print(top_diff("NF", "GAP").to_string(index=False))
    d_all = top_diff("NF", "GAP", k=len(names))
    big = d_all[d_all["d (std)"].abs() > 1]
    print("\nJumlah fitur dengan |d| > 1 antara NF dan GAP: {} dari {} (metrics {}, aktivitas trace/log {})".format(
        len(big), len(names), int(big["fitur"].str.startswith("m:").sum()), int((~big["fitur"].str.startswith("m:")).sum())))

    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler
    fault_runs = [i for i, m in manifest.items() if m["kind"] == "fault"]
    nf_runs = [i for i, m in manifest.items() if m["kind"] == "no_fault"]
    folds = [(set(fault_runs[j::3]), {nf_runs[j]}) for j in range(3)]  # tiap lipatan menahan 3 run berfault + 1 run tanpa fault

    def loro_auc(g_neg, g_pos, cols):
        sub = meta[meta["grp"].isin([g_neg, g_pos])].iloc[::5]  # stride 5 detik: kurangi autokorelasi dan waktu
        Xs, ys, rs = X[sub.index][:, cols], (sub["grp"] == g_pos).to_numpy().astype(int), sub["run"].to_numpy()
        scores, truth = [], []
        for fr, nr in folds:
            te_m = np.isin(rs, list(fr | nr))
            if len(set(ys[~te_m])) < 2 or len(set(ys[te_m])) < 2:
                continue
            sc = StandardScaler().fit(Xs[~te_m])
            clf = LogisticRegression(max_iter=300, C=0.1).fit(sc.transform(Xs[~te_m]), ys[~te_m])
            scores.append(clf.predict_proba(sc.transform(Xs[te_m]))[:, 1]); truth.append(ys[te_m])
        return roc_auc_score(np.concatenate(truth), np.concatenate(scores)) if scores else float("nan")

    allc, mc, ac = np.arange(len(names)), np.where(is_m)[0], np.where(is_act)[0]
    print("\nAUC classifier logistic (leave-run-group-out; 0,5 = tak bisa dibedakan, 1,0 = sangat terpisah):")
    rows = []
    for gn, gp in (("NF", "GAP"), ("GAP", "FLT"), ("NF", "FLT")):
        rows.append({"kasus": "{} vs {}".format(gn, gp), "semua fitur": round(loro_auc(gn, gp, allc), 3),
                     "hanya metrics": round(loro_auc(gn, gp, mc), 3), "hanya aktivitas trace+log": round(loro_auc(gn, gp, ac), 3)})
    print(pd.DataFrame(rows).to_string(index=False))

    # Classifier linear pada fitur per-node tak bisa menangkap "ada node yang anomali di mana saja" (biang berbeda-beda per jendela).
    # Ringkasan antar-node + pohon gradient boosting: lebih adil untuk bertanya "apakah kelompok ini bisa dibedakan?"
    from sklearn.ensemble import HistGradientBoostingClassifier
    Z = X[:, :len(SV) * len(M)].reshape(len(X), len(SV), len(M))
    summ = np.concatenate([np.abs(Z).max(axis=1), Z.mean(axis=1), Z.std(axis=1), np.percentile(np.abs(Z), 90, axis=1),
                           X[:, len(SV) * len(M):len(SV) * len(M) + len(SV)].sum(axis=1, keepdims=True),
                           X[:, len(SV) * len(M) + len(SV):].sum(axis=1, keepdims=True)], axis=1)

    def loro_auc_gb(g_neg, g_pos, cols):
        sub = meta[meta["grp"].isin([g_neg, g_pos])].iloc[::5]
        Xs, ys, rs = summ[sub.index][:, cols], (sub["grp"] == g_pos).to_numpy().astype(int), sub["run"].to_numpy()
        sc_, tr_ = [], []
        for fr, nr in folds:
            te_m = np.isin(rs, list(fr | nr))
            if len(set(ys[~te_m])) < 2 or len(set(ys[te_m])) < 2:
                continue
            clf = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.1, random_state=0).fit(Xs[~te_m], ys[~te_m])
            sc_.append(clf.predict_proba(Xs[te_m])[:, 1]); tr_.append(ys[te_m])
        return roc_auc_score(np.concatenate(tr_), np.concatenate(sc_)) if sc_ else float("nan")

    nm = len(M) * 4
    print("\nAUC gradient boosting pada RINGKASAN ANTAR-NODE (max|z|, rata-rata, sd, persentil-90 per kanal; jumlah node ber-trace/ber-log):")
    rows = []
    for gn, gp in (("NF", "GAP"), ("GAP", "FLT"), ("NF", "FLT")):
        rows.append({"kasus": "{} vs {}".format(gn, gp), "semua ringkasan": round(loro_auc_gb(gn, gp, np.arange(summ.shape[1])), 3),
                     "hanya metrics": round(loro_auc_gb(gn, gp, np.arange(nm)), 3),
                     "hanya aktivitas trace+log": round(loro_auc_gb(gn, gp, np.arange(nm, summ.shape[1])), 3)})
    print(pd.DataFrame(rows).to_string(index=False))

    groups_ch = {"memory (3,4)": [3, 4], "cpu (0,1,2)": [0, 1, 2], "network rx/tx (5,6)": [5, 6]}
    print("\nAUC gradient boosting per KELOMPOK KANAL (ringkasan antar-node dari kanal itu saja):")
    rows = []
    for gname, chs in groups_ch.items():
        cols = np.array([b * len(M) + c for b in range(4) for c in chs])
        row = {"kelompok kanal": gname}
        for gn, gp in (("NF", "GAP"), ("GAP", "FLT"), ("NF", "FLT")):
            row["{} vs {}".format(gn, gp)] = round(loro_auc_gb(gn, gp, cols), 3)
        rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))

    print("\nPergeseran fitur di run TANPA fault: separuh awal (0–50%) vs 40% akhir (60–100%) (d dalam simpangan baku separuh awal)")
    for r in nf_runs:
        sel = meta[meta["run"] == r]
        t0, t1 = records[r]["start"], records[r]["end"]
        pos = (sel["start"] - t0) / (t1 - t0)
        e, l = X[sel.index[pos < 0.5]], X[sel.index[pos >= 0.6]]
        d = (l.mean(axis=0) - e.mean(axis=0)) / (e.std(axis=0) + 1e-6)
        o = np.argsort(-np.abs(d))[:6]
        print("run {}: fitur |d|>1 = {} dari {} | teratas: {}".format(
            r, int((np.abs(d) > 1).sum()), len(names), ", ".join("{} ({:+.1f})".format(names[i], d[i]) for i in o)))

# ---------------------------------------------------------------- D
if "D" in parts:
    print("=" * 100 + "\nD. Run TANPA fault: kanal metrics mentah yang levelnya berubah antara separuh awal dan 40% akhir (dan kapan)\n" + "=" * 100)
    for idx, m in manifest.items():
        if m["kind"] != "no_fault":
            continue
        n_ = m["end"] - m["start"] + 1
        rows = []
        for sv, s_ in zip(SV, info.service_names):
            df = pd.read_csv(os.path.join(parsed, "metrics{}".format(idx), s_ + ".csv")).set_index("timestamp")
            for c in M:
                x = df[c].to_numpy(dtype=float)
                first, last = x[: int(0.5 * len(x))], x[int(0.6 * len(x)):]
                lf, ll = np.median(first), np.median(last)
                rel = abs(ll - lf) / (abs(lf) + 1e-12)
                # skala level pertama: seberapa besar variasi normal di separuh awal, dibanding perubahannya
                sd = np.std(first) + 1e-12
                if rel > 0.2 and abs(ll - lf) > 3 * sd:
                    mid = (lf + ll) / 2
                    roll = pd.Series(x).rolling(61, center=True, min_periods=1).median().to_numpy()
                    cross = np.where((roll - mid) * (np.sign(ll - lf)) > 0)[0]
                    rows.append({"service": sv, "kanal": c, "level awal": lf, "level akhir": ll, "perubahan relatif": round(rel, 2),
                                 "waktu perubahan (% run)": round(100 * (cross[0] if len(cross) else np.nan) / len(x), 0)})
        print("run {} ({} detik; separuh awal = latih, 50–60% = val): {} kanal berubah level".format(idx, n_, len(rows)))
        if rows:
            print(pd.DataFrame(rows).sort_values("perubahan relatif", ascending=False).head(8).to_string(index=False))
        print()

# ---------------------------------------------------------------- C
if "C" in parts:
    print("=" * 100 + "\nC. Alarm palsu (jendela normal) per 200 detik di run tanpa fault\n" + "=" * 100)
    df = pd.read_csv(os.path.join(a.result_dir, a.run, "diagnosis_alarm.csv"))
    df = df[(df["kind"] == "no_fault") & (df["culprit"] < 0)].copy()
    df["bin"] = ((df["start"] - df.groupby("run")["start"].transform("min")) // 200 * 200).astype(int)
    tab = df.pivot_table(index="bin", columns="run", values="alarm", aggfunc="mean").mul(100).round(0)
    tab["split dominan"] = df.groupby("bin")["split"].agg(lambda s: s.value_counts().index[0])
    print(tab.to_string())
