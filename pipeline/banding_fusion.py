#!/usr/bin/env python3
"""Bandingkan F3 (gmu) dengan F1 (concat_glu) dan F2 (concat_fc) di T = 10, 15 epoch, kedua skema.

Pakai (dari akar proyek):  work/envs/train312/bin/python -I pipeline/banding_fusion.py
Metrik Test (std) pada epoch yang dipilih Val (sama dengan rekap_semua.py). Turunan: FPR = FP / n_normal dengan
TP = Rec * n_gangguan, FP = TP * (1/Pre - 1); HR@1 bersyarat = HR@1 / Rec. Selisih = F3 - baseline, CI 95% Welch
(* = CI tidak memuat 0), p = uji permutasi dua sisi atas semua 252 pembagian 10 nilai.
"""
import sys, os, pickle, itertools, statistics as st, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import rekap_semua as R
runs = [r for r in R.load() if r["T"] == 10 and r["epochs"] == 15 and r["scheme"] in ("within_event", "leave_event_out")]
cnt = {}
for sc in ("within_event", "leave_event_out"):
    d = pickle.load(open("work/chunks/A1/%s/chunk_test.pkl" % sc, "rb"))
    ys = [v["culprit"] for v in d.values()] if isinstance(d, dict) else None
    pos = sum(1 for y in ys if y != -1); cnt[sc] = (pos, len(ys) - pos)
print("test (gangguan, normal):", cnt)
def derived(r):
    t = r["t"]; P, N = cnt[r["scheme"]]
    tp = t["Rec(std)"] * P; fp = tp * (1 / t["Pre(std)"] - 1)
    return dict(F1=t["F1(std)"], Pre=t["Pre(std)"], Rec=t["Rec(std)"], HR1=t["HR@1(std)"], HR3=t["HR@3(std)"],
                NDCG3=t["ndcg@3(std)"], FPR=fp / N, HR1c=t["HR@1(std)"] / t["Rec(std)"])
def perm(a, b):
    obs = st.mean(b) - st.mean(a); allv = a + b; n = len(a); c = tot = 0
    for idx in itertools.combinations(range(len(allv)), n):
        A = [allv[i] for i in idx]; B = [allv[i] for i in range(len(allv)) if i not in idx]
        tot += 1; c += abs(st.mean(B) - st.mean(A)) >= abs(obs) - 1e-12
    return c / tot
F = {"concat_glu": "F1", "concat_fc": "F2", "gmu": "F3"}
for sc in ("within_event", "leave_event_out"):
    print("\n##", sc)
    D = {}
    for f in F:
        rs = sorted([r for r in runs if r["scheme"] == sc and r["fusion"] == f], key=lambda r: R.SEEDS.index(r["seed"]))
        D[f] = [derived(r) for r in rs]
        print(F[f], "seeds", [r["seed"] for r in rs], "ep", [r["ep"] for r in rs], "s/epoch %.0f" % st.mean(r["sec"] for r in rs))
    for m in ["F1", "Pre", "Rec", "HR1", "HR3", "NDCG3", "FPR", "HR1c"]:
        row = [m] + ["%.3f±%.3f" % (st.mean(x[m] for x in D[f]), st.stdev(x[m] for x in D[f])) for f in F]
        for base in ("concat_glu", "concat_fc"):
            a = [x[m] for x in D[base]]; b = [x[m] for x in D["gmu"]]
            dd, lo, hi = R.welch(a, b)[:3]
            row.append("F3-%s %+.3f [%+.3f,%+.3f]%s p=%.3f" % (F[base], dd, lo, hi, " *" if lo > 0 or hi < 0 else "", perm(a, b)))
        print(" | ".join(row))
    print("per seed F3:", {m: [round(x[m], 3) for x in D["gmu"]] for m in ("F1", "HR1", "FPR")})
