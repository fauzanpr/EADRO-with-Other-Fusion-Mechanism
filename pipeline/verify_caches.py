"""Verifikasi independen cache per run (traces.pkl / metrics.pkl / logs.pkl) terhadap parsed_data.

Untuk logs: hitung ulang jumlah kejadian log per (jendela, node, event) langsung dari logs{idx}.csv, lalu periksa
  - (jendela, node) yang punya fitur Hawkes != 0  <=>  node itu punya >= 1 baris log di jendela itu
  - bagaimana nilai Hawkes (baseline) merespons jumlah kejadian
Untuk metrics/traces: bentuk dan kewarasan nilai (traces sudah dicocokkan lebih rinci oleh verify_with_eadro.py).

Pakai:  python -I verify_caches.py --work-dir ".../work" --name A1
"""
import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I tidak menambahkannya
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from common import Info  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--work-dir", required=True)
parser.add_argument("--name", required=True)
parser.add_argument("--chunk-lenth", type=int, default=10)
args = parser.parse_args()

work = os.path.abspath(args.work_dir)
parsed = os.path.join(work, "preprocess", "parsed_data", args.name)
info = Info("trainticket")
L = args.chunk_lenth
templates = json.load(open(os.path.join(parsed, "templates.json")))
E = len(templates) + 1
event2id = {t: i + 1 for i, t in enumerate(templates)}
n_runs = len([f for f in os.listdir(parsed) if f.startswith("records")])

BUCKETS = [(0, 0), (1, 1), (2, 2), (3, 5), (6, 10), (11, 10 ** 9)]
bucket_vals = {b: [] for b in BUCKETS}
rank_a, rank_c = [], []

print("{:>3s} {:>8s} {:>20s} {:>8s} {:>10s} {:>10s}".format("idx", "jendela", "logs.pkl", "aktif", "mismatch", "unik"))
for idx in range(n_runs):
    rec = json.load(open(os.path.join(parsed, "records{}.json".format(idx))))
    start, end = rec["start"], rec["end"]
    n_win = end - L + 1 - start  # = len(range(start, end-L+1))
    cdir = os.path.join(work, "chunks", args.name, str(idx))
    with open(os.path.join(cdir, "logs.pkl"), "rb") as f:
        logs = pickle.load(f)
    with open(os.path.join(cdir, "metrics.pkl"), "rb") as f:
        metrics = pickle.load(f)
    with open(os.path.join(cdir, "traces.pkl"), "rb") as f:
        traces = pickle.load(f)
    assert logs.shape == (n_win, info.node_num, E), logs.shape
    assert metrics.shape == (n_win, info.node_num, L, len(info.metric_names)), metrics.shape
    assert traces["latency"].shape == (n_win, info.node_num, L, 1), traces["latency"].shape
    for arr in (logs, metrics, traces["latency"]):
        assert np.isfinite(arr).all()

    df = pd.read_csv(os.path.join(parsed, "logs{}.csv".format(idx)))
    assert not df["event"].isna().any()
    counts = np.zeros((n_win, info.node_num, E), dtype=np.int32)
    node = df["service"].map(info.service2nid).to_numpy()
    ev = df["event"].map(lambda x: event2id.get(x, 0)).to_numpy()
    t = df["timestamp"].to_numpy() - start
    for k in range(L):  # baris pada detik t masuk ke jendela mulai s dengan s <= t <= s+L-1  => s = t-k
        w = t - k
        ok = (w >= 0) & (w < n_win)
        np.add.at(counts, (w[ok], node[ok], ev[ok]), 1)

    active_expected = counts.sum(axis=2) > 0
    active_got = np.abs(logs).sum(axis=2) > 0
    mismatch = int((active_expected != active_got).sum())
    assert mismatch == 0, "run {}: {} pasangan (jendela,node) tidak cocok".format(idx, mismatch)

    a, c = logs[active_expected], counts[active_expected]
    for lo, hi in BUCKETS:
        sel = (c >= lo) & (c <= hi)
        if sel.any():
            bucket_vals[(lo, hi)].append(a[sel])
    rank_a.append(a.ravel()[::37]); rank_c.append(c.ravel()[::37])  # subsampel untuk korelasi
    print("{:3d} {:8d} {:>20s} {:8d} {:10d} {:10d}".format(
        idx, n_win, str(logs.shape), int(active_expected.sum()), mismatch, len(np.unique(np.round(a, 6)))))

print("\nRespons nilai Hawkes (baseline) terhadap jumlah kejadian event, pada pasangan (jendela,node) yang punya log:")
print("{:>14s} {:>10s} {:>9s} {:>9s} {:>9s} {:>9s}".format("jumlah kejadian", "entri", "median", "rata2", "p5", "p95"))
for (lo, hi), parts in bucket_vals.items():
    v = np.concatenate(parts)
    label = "{}".format(lo) if lo == hi else ("{}-{}".format(lo, hi) if hi < 10 ** 9 else ">={}".format(lo))
    print("{:>14s} {:10d} {:9.4f} {:9.4f} {:9.4f} {:9.4f}".format(label, v.size, np.median(v), v.mean(), np.percentile(v, 5), np.percentile(v, 95)))
ra, rc = np.concatenate(rank_a), np.concatenate(rank_c)
print("Korelasi Spearman(baseline, jumlah kejadian) pada subsampel {} entri: {:.3f}".format(
    ra.size, pd.Series(ra).corr(pd.Series(rc), method="spearman")))
print("\nSemua cache cocok dengan parsed_data.")
