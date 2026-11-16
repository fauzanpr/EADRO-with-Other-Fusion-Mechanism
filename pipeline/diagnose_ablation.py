"""Diagnosis oklusi: input mana yang memicu alarm model pada jendela normal? (hanya membaca; model dan data tidak diubah)

Model yang sudah dilatih dijalankan pada subsampel jendela (tiap 4 detik) dengan satu kelompok input diganti nol (nol = nilai rata-rata
z-score pada kondisi biasa). Dibandingkan: tanpa gangguan input, tanpa log, tanpa trace, tanpa semua metrics, dan tanpa kelompok kanal
cpu / memory / network. Penggantian nol bukan data asli, jadi bacalah sebagai PETUNJUK arah, bukan bukti pasti.

Kelompok jendela: NF (normal, run tanpa fault) per pembagian data, GAP (normal, run berfault), FLT (bergangguan; recall deteksi).

Pakai:  work/envs/train312/bin/python -I pipeline/diagnose_ablation.py --run 9df622b8
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "Eadro", "codes"))

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True)
ap.add_argument("--scheme", default="within_event")
ap.add_argument("--result-dir", default=os.path.join(ROOT, "work", "result"))
ap.add_argument("--stride", type=int, default=4)
a = ap.parse_args()

run_dir = os.path.join(a.result_dir, a.run)
params = json.load(open(os.path.join(run_dir, "params.json")))
data_dir = os.path.join(ROOT, "work", "chunks", "A1", a.scheme)
parsed = os.path.join(ROOT, "work", "preprocess", "parsed_data", "A1")
sys.argv = ["main.py", "--data", params["data"]]
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402
import main  # noqa: E402
from base import BaseModel  # noqa: E402
from utils import load_chunks, read_json  # noqa: E402

meta = read_json(os.path.join(data_dir, "metadata.json"))
manifest = {m["idx"]: m for m in json.load(open(os.path.join(parsed, "manifest.json")))}
kw = dict(params)
kw.update(hash_id=a.run, result_dir=a.result_dir)
model = BaseModel(meta["event_num"], meta["metric_num"], meta["node_num"], torch.device("cpu"), **kw)
model.load_model(os.path.join(run_dir, "model.ckpt"))
model.model.eval()

tr, va, te = load_chunks(data_dir)
picked, rows = {}, []
for split, chunks in (("train", tr), ("val", va), ("test", te)):
    for k, v in chunks.items():
        if v["start"] % a.stride:
            continue
        grp = "NF" if manifest[v["run"]]["kind"] == "no_fault" else ("FLT" if v["culprit"] >= 0 else "GAP")
        picked[(split, k)] = v
        rows.append((split, k, v["run"], grp, v["culprit"], v["fault_type"]))
del tr, va, te
info = pd.DataFrame(rows, columns=["split", "key", "run", "grp", "culprit", "ftype"])
ds = main.chunkDataset({i: picked[(s, k)] for i, (s, k) in enumerate(zip(info["split"], info["key"]))}, meta["node_num"], tuple(meta["edges"]))
base = {"logs": ds.logs.clone(), "metrics": ds.metrics.clone(), "traces": ds.traces.clone()}
print("jendela dinilai: {} (stride {} detik)".format(len(ds), a.stride), flush=True)

# kelompok kanal metrics: urutan CSV cpu_usage_system, cpu_usage_total, cpu_usage_user, memory_usage, memory_working_set, rx_bytes, tx_bytes
VARIANTS = {
    "tanpa ablasi": {},
    "tanpa log": {"logs": None},
    "tanpa trace": {"traces": None},
    "tanpa SEMUA metrics": {"metrics": slice(None)},
    "tanpa cpu": {"metrics": [0, 1, 2]},
    "tanpa memory": {"metrics": [3, 4]},
    "tanpa network (rx/tx)": {"metrics": [5, 6]},
}


def alarm_vector(spec):
    ds.logs, ds.metrics, ds.traces = base["logs"].clone(), base["metrics"].clone(), base["traces"].clone()
    for key, idx in spec.items():
        if key == "logs":
            ds.logs.zero_()
        elif key == "traces":
            ds.traces.zero_()
        else:
            ds.metrics[..., idx] = 0.0
    dl = DataLoader(ds, batch_size=512, shuffle=False, collate_fn=main.make_collate(ds.graph))
    out = []
    with torch.no_grad():
        for g, y in dl:
            out.append((model.model.detecter(model.model.encoder(g)).argmax(dim=1) == 1).numpy())
    return np.concatenate(out)


res = {name: alarm_vector(spec) for name, spec in VARIANTS.items()}
cats = {
    "NF  train (normal, run tanpa fault)": (info["grp"] == "NF") & (info["split"] == "train"),
    "NF  val": (info["grp"] == "NF") & (info["split"] == "val"),
    "NF  test run 9": (info["grp"] == "NF") & (info["split"] == "test") & (info["run"] == 9),
    "NF  test run 10": (info["grp"] == "NF") & (info["split"] == "test") & (info["run"] == 10),
    "NF  test run 11": (info["grp"] == "NF") & (info["split"] == "test") & (info["run"] == 11),
    "GAP train (normal, run berfault)": (info["grp"] == "GAP") & (info["split"] == "train"),
    "GAP test": (info["grp"] == "GAP") & (info["split"] == "test"),
    "FLT test (recall deteksi)": (info["grp"] == "FLT") & (info["split"] == "test"),
}
tab = pd.DataFrame({name: {c: round(100 * res[name][m.to_numpy()].mean(), 1) for c, m in cats.items()} for name in VARIANTS})
tab.insert(0, "n", [int(m.sum()) for m in cats.values()])
pd.set_option("display.width", 220)
print("\n% jendela yang diberi ALARM (untuk NF dan GAP: makin kecil makin baik; untuk FLT: makin besar makin baik)")
print(tab.to_string())
tab.to_csv(os.path.join(run_dir, "diagnosis_ablasi.csv"))
print("\nDisimpan di", os.path.join(run_dir, "diagnosis_ablasi.csv"))


# ---- Bagian 2: memakai kanal service BIANG sendiri, atau kanal service lain? (hanya jendela bergangguan di Test)
print("\n" + "=" * 100)
print("Jendela bergangguan (Test): %% terdeteksi bila kanal tertentu dinolkan HANYA di service biang, atau HANYA di semua service lain")
print("=" * 100)
flt = ((info["grp"] == "FLT") & (info["split"] == "test")).to_numpy()
cul = torch.tensor(np.where(info["culprit"].to_numpy() >= 0, info["culprit"].to_numpy(), 0))
N = len(info)
ar = torch.arange(N)
other_mask = torch.ones(N, meta["node_num"], dtype=torch.bool)
other_mask[ar, cul] = False


def alarm_nodewise(channels, where):
    ds.logs, ds.metrics, ds.traces = base["logs"].clone(), base["metrics"].clone(), base["traces"].clone()
    for ch in channels:
        if where == "biang":
            ds.metrics[ar, cul, :, ch] = 0.0
        else:
            view = ds.metrics[..., ch]  # [N, node, T] (view)
            view[other_mask] = 0.0
    dl = DataLoader(ds, batch_size=512, shuffle=False, collate_fn=main.make_collate(ds.graph))
    out = []
    with torch.no_grad():
        for g, y in dl:
            out.append((model.model.detecter(model.model.encoder(g)).argmax(dim=1) == 1).numpy())
    return np.concatenate(out)


spec2 = {"tanpa ablasi": ([], "biang"), "memory di BIANG saja": ([3, 4], "biang"), "memory di service LAIN saja": ([3, 4], "lain"),
         "cpu di BIANG saja": ([0, 1, 2], "biang"), "cpu di service LAIN saja": ([0, 1, 2], "lain"),
         "network di BIANG saja": ([5, 6], "biang"), "network di service LAIN saja": ([5, 6], "lain")}
res2 = {name: alarm_nodewise(ch, wh) for name, (ch, wh) in spec2.items()}
t2 = pd.DataFrame({name: {ft: round(100 * res2[name][flt & (info["ftype"] == ft).to_numpy()].mean(), 1) for ft in ["cpu_load", "network_delay", "network_loss"]}
                   for name in spec2})
t2.insert(0, "n", [int((flt & (info["ftype"] == ft).to_numpy()).sum()) for ft in ["cpu_load", "network_delay", "network_loss"]])
print(t2.to_string())
t2.to_csv(os.path.join(run_dir, "diagnosis_ablasi_node.csv"))
