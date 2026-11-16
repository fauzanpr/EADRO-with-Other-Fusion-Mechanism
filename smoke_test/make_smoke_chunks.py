"""Bikin chunk sintetis berformat sama dengan keluaran preprocess/align.py.

Format per chunk (lihat align.py:63-67 dan single_process.py):
    traces  [node_num, T, 1]          latensi rata-rata per slot (univariate, sesuai paper)
    metrics [node_num, T, metric_num] 7 KPI, sudah z-score
    logs    [node_num, event_num]     parameter Hawkes per event
    culprit int                       nid biang kerok, -1 jika normal

Chunk berfault diberi sinyal pada node culprit supaya model *bisa* belajar.
Dipakai hanya untuk smoke test; BUKAN data TT.
"""
import json
import os
import pickle
import random
import string
import sys

import numpy as np

repo_codes, out_dir = sys.argv[1], sys.argv[2]
SIGNAL = sys.argv[3] if len(sys.argv) > 3 else "generic"  # generic | node
sys.path.insert(0, os.path.join(repo_codes, "preprocess"))
from util import Info  # noqa: E402  (Info('trainticket') -> 27 node + edges)

rng = np.random.default_rng(0)
random.seed(0)
info = Info("trainticket")
CHUNKS = int(sys.argv[4]) if len(sys.argv) > 4 else 800
N, T, M = info.node_num, 10, len(info.metric_names)
EVENTS = N + 1 if SIGNAL == "node" else 21  # node: tiap service punya 1 event khas (+1 'unseen'), seperti template log asli


def make_chunk(culprit):
    traces = rng.normal(0, 1, (N, T, 1))
    metrics = rng.normal(0, 1, (N, T, M))
    logs = rng.uniform(0, 0.2, (N, EVENTS))
    if culprit >= 0 and SIGNAL == "node":
        traces[culprit, 5:, 0] += 3.0
        metrics[culprit, 5:, culprit % M] += 3.0
        logs[culprit, culprit + 1] += 1.0
    elif culprit >= 0:
        traces[culprit, 5:, 0] += 3.0
        metrics[culprit, 5:, :3] += 3.0
        logs[culprit, :5] += 1.0
    return {"traces": traces, "metrics": metrics, "logs": logs, "culprit": culprit}


ids, chunks = set(), {}
while len(chunks) < CHUNKS:
    cid = "".join(random.sample(string.ascii_letters + string.digits, 8))
    if cid in ids:
        continue
    ids.add(cid)
    culprit = -1 if rng.random() < 0.4 else int(rng.integers(N))
    chunks[cid] = make_chunk(culprit)

keys = list(chunks)
random.shuffle(keys)
cut, cut_val = int(0.6 * len(keys)), int(0.75 * len(keys))
train = {k: chunks[k] for k in keys[:cut]}
val = {k: chunks[k] for k in keys[cut:cut_val]}
test = {k: chunks[k] for k in keys[cut_val:]}

os.makedirs(out_dir, exist_ok=True)
for name, obj in [("chunk_train.pkl", train), ("chunk_val.pkl", val), ("chunk_test.pkl", test)]:
    with open(os.path.join(out_dir, name), "wb") as fw:
        pickle.dump(obj, fw)

info.add_info("chunk_lenth", T)
info.add_info("chunk_num", len(chunks))
info.add_info("edges", info.edges)
info.add_info("event_num", EVENTS)
with open(os.path.join(out_dir, "metadata.json"), "w") as fw:
    json.dump(info.metadata, fw)

normal = sum(c["culprit"] == -1 for c in chunks.values())
print(f"nodes={N} T={T} metrics={M} events={EVENTS} | chunks={len(chunks)} "
      f"(train {len(train)}, val {len(val)}, test {len(test)}) | normal={normal} faulty={len(chunks) - normal}")
print(f"edges={len(info.edges[0])} | ditulis ke {out_dir}")
