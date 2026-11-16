"""Diagnosis kesenjangan deteksi Val -> Test: siapa saja jendela NORMAL yang diberi alarm palsu?

Memuat model.ckpt sebuah run, menjalankan model pada chunk Train/Val/Test, lalu memecah tingkat alarm (prob. gangguan > 0,5, sama dengan
keputusan evaluate()) menurut:
  - jenis run: run tanpa fault vs run berfault
  - run tanpa fault: posisi waktu dalam run (sepertiga awal / tengah / akhir) dan pembagian data (train/val/test)
  - run berfault: jarak ke kejadian fault terdekat (sebelum / sesudah)
  - jendela bergangguan: recall deteksi dan top-1 lokalisasi per jenis fault
  - pergeseran fitur metrics (z-score) antara bagian awal dan akhir run tanpa fault
Hanya membaca; tidak mengubah data maupun model.

Pakai:  work/envs/train312/bin/python -I pipeline/diagnose_alarm.py --run 9df622b8 [--scheme within_event]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "Eadro", "codes"))

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, help="hash_id folder di work/result/")
ap.add_argument("--scheme", default="within_event")
ap.add_argument("--result-dir", default=os.path.join(ROOT, "work", "result"))
ap.add_argument("--batch-size", type=int, default=512)
a = ap.parse_args()

run_dir = os.path.join(a.result_dir, a.run)
params = json.load(open(os.path.join(run_dir, "params.json")))
assert params["data"].endswith(a.scheme), "run ini dilatih pada {}, bukan {}".format(params["data"], a.scheme)
data_dir = os.path.join(ROOT, "work", "chunks", "A1", a.scheme)
parsed = os.path.join(ROOT, "work", "preprocess", "parsed_data", "A1")

sys.argv = ["main.py", "--data", params["data"]]  # main.py membaca argv saat di-import
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402
import main  # noqa: E402
from base import BaseModel  # noqa: E402
from utils import load_chunks, read_json  # noqa: E402

meta = read_json(os.path.join(data_dir, "metadata.json"))
manifest = {m["idx"]: m for m in json.load(open(os.path.join(parsed, "manifest.json")))}
records = {i: json.load(open(os.path.join(parsed, "records{}.json".format(i)))) for i in manifest}
L = meta["chunk_lenth"]

device = torch.device("cpu")
kw = dict(params)
kw.update(hash_id=a.run, result_dir=a.result_dir)
model = BaseModel(meta["event_num"], meta["metric_num"], meta["node_num"], device, **kw)
model.load_model(os.path.join(run_dir, "model.ckpt"))
model.model.eval()
torch.set_num_threads(max(1, os.cpu_count() or 1))

tr, va, te = load_chunks(data_dir)
edges = tuple(meta["edges"])
rows = []
for split, chunks in (("train", tr), ("val", va), ("test", te)):
    ds = main.chunkDataset(chunks, meta["node_num"], edges)
    dl = DataLoader(ds, batch_size=a.batch_size, shuffle=False, collate_fn=main.make_collate(ds.graph))
    p_anom, top1 = [], []
    with torch.no_grad():
        for g, y in dl:
            emb = model.model.encoder(g)
            p_anom.append(torch.softmax(model.model.detecter(emb), dim=1)[:, 1].numpy())
            top1.append(model.model.localizer(emb).argmax(dim=1).numpy())
    ids = list(ds.idx2id.values())
    df = pd.DataFrame({"split": split, "run": [chunks[i]["run"] for i in ids], "start": [chunks[i]["start"] for i in ids],
                       "culprit": [chunks[i]["culprit"] for i in ids], "fault_type": [chunks[i]["fault_type"] for i in ids],
                       "p_anom": np.concatenate(p_anom), "top1": np.concatenate(top1)})
    # rata-rata |z| semua metrics (atas node, waktu, kanal) per jendela, untuk melihat pergeseran fitur
    df["abs_z"] = ds.metrics.abs().mean(dim=(1, 2, 3)).numpy()  # metrics: [N, node, T, 7]
    rows.append(df)
    print("{}: {} jendela diproses".format(split, len(df)), flush=True)
    del ds, dl, chunks

df = pd.concat(rows, ignore_index=True)
df["alarm"] = df["p_anom"] > 0.5
df["kind"] = df["run"].map(lambda r: manifest[r]["kind"])
df["faulty"] = df["culprit"] >= 0
df["pos"] = [(s - records[r]["start"]) / (records[r]["end"] - records[r]["start"]) for r, s in zip(df["run"], df["start"])]
df["posbin"] = pd.cut(df["pos"], [0, 1 / 3, 2 / 3, 1.0001], labels=["awal", "tengah", "akhir"], include_lowest=True)


def nearest_fault(r, s):
    """(jarak detik, 'sebelum'/'sesudah') ke kejadian fault terdekat; jendela = [s, s+L-1]."""
    best = (10 ** 9, "-")
    for f in records[r]["faults"]:
        if s + L - 1 < f["s"]:
            d, side = f["s"] - (s + L - 1), "sebelum fault"
        elif s > f["e"]:
            d, side = s - f["e"], "sesudah fault"
        else:
            continue
        if d < best[0]:
            best = (d, side)
    return best


nf = [nearest_fault(r, s) if (not c >= 0 and manifest[r]["kind"] == "fault") else (np.nan, "-")
      for r, s, c in zip(df["run"], df["start"], df["culprit"])]
df["dist"] = [x[0] for x in nf]
df["side"] = [x[1] for x in nf]
df["distbin"] = pd.cut(df["dist"], [0, 10, 30, 60, 120, 10 ** 9], labels=["1-10 s", "11-30 s", "31-60 s", "61-120 s", ">120 s"])


def rate(g):
    return pd.Series({"jendela": len(g), "alarm": int(g["alarm"].sum()), "%alarm": round(100 * g["alarm"].mean(), 1)})


pd.set_option("display.width", 200)
normal = df[~df["faulty"]]
print("\n=== 1. Alarm palsu pada jendela NORMAL per pembagian data (alarm yang seharusnya 0%) ===")
print(normal.groupby("split").apply(rate).loc[["train", "val", "test"]].to_string())
print("\n=== 2. ... dipecah per jenis run ===")
print(normal.groupby(["split", "kind"]).apply(rate).to_string())
print("\n=== 3. Run TANPA fault: alarm palsu menurut posisi waktu dalam run (awal/tengah/akhir) ===")
print(normal[normal["kind"] == "no_fault"].groupby(["posbin", "split"], observed=True).apply(rate).to_string())
print("\n=== 4. Run TANPA fault: per run dan pembagian data ===")
print(normal[normal["kind"] == "no_fault"].groupby(["run", "split"]).apply(rate).to_string())
print("\n=== 5. Run BERFAULT: alarm palsu menurut jarak ke fault terdekat (jendela normal) ===")
print(normal[normal["kind"] == "fault"].groupby(["split", "side", "distbin"], observed=True).apply(rate).to_string())

print("\n=== 6. Jendela BERGANGGUAN: deteksi (recall) dan top-1 lokalisasi per jenis fault ===")
fa = df[df["faulty"]].copy()
fa["top1_ok"] = fa["top1"] == fa["culprit"]
print(fa.groupby(["split", "fault_type"]).apply(lambda g: pd.Series({
    "jendela": len(g), "%terdeteksi": round(100 * g["alarm"].mean(), 1), "%top1 benar (semua)": round(100 * g["top1_ok"].mean(), 1),
    "%top1 benar (yg terdeteksi)": round(100 * g.loc[g["alarm"], "top1_ok"].mean(), 1)})).to_string())

print("\n=== 7. Pergeseran fitur metrics di run TANPA fault: |z| rata-rata awal vs akhir (satuan z-score) ===")
nof = df[df["kind"] == "no_fault"]
print(nof.groupby(["posbin", "split"], observed=True)["abs_z"].agg(["count", "mean"]).round(3).to_string())
fz = df[(df["kind"] == "fault") & (~df["faulty"])]
print("pembanding: jendela normal di run berfault, |z| rata-rata = {:.3f}".format(fz["abs_z"].mean()))

out = os.path.join(run_dir, "diagnosis_alarm.csv")
df.drop(columns=["posbin", "distbin"]).to_csv(out, index=False)
print("\nPrediksi per jendela disimpan di", out)
