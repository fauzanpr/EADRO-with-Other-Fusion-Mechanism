"""Langkah 3b: rakit chunk dari cache per run, lalu bagi train/val/test TANPA kebocoran waktu.

Beda dengan align.split_chunks (acak per jendela, jendela bertetangga berbagi 9 dari 10 detik):
  - setiap DETIK diberi label split; sebuah jendela dipakai hanya jika semua detiknya berlabel sama,
    jendela yang melintasi batas split dibuang (purge) -> tidak ada detik yang dipakai bersama train dan test
  - ada validation set (untuk memilih epoch), terpisah dari test

Unit waktu ("wilayah"): tiap kejadian fault beserta separuh celah normal di kiri-kanannya; run tanpa fault = satu wilayah.
Skema:
  within_event     : tiap wilayah dipotong menurut waktu: 50% awal train, 10% val, 40% akhir test.
                     Semua kombinasi (service, jenis fault) ada di train. Paling dekat dengan teks paper.
  leave_event_out  : untuk tiap service, SATU jenis fault (bergilir cpu_load / network_delay / network_loss menurut nid)
                     seluruhnya jadi test; run tanpa fault terakhir juga test. Wilayah lain: 85% train, 15% val (akhir).
                     Menguji generalisasi ke jenis fault yang belum pernah dilihat untuk service itu.
  random_original  : TIRUAN protokol kode asli (align.split_chunks): semua jendela diacak, 70% train / 30% test
                     (--test-ratio), TANPA purge, sehingga jendela bertetangga (berbagi T-1 detik) tersebar di
                     train dan test (bocor waktu). Tidak ada val terpisah: chunk_val = salinan chunk_test, sehingga
                     epoch dipilih memakai test, persis seperti kode asli. Beda dengan aslinya: pengacakan memakai
                     --split-seed (kode asli tanpa seed). HANYA untuk mendekati angka paper, bukan protokol adil.

Label culprit memakai align.get_basic ASLI. Jalankan dengan Python 3.8 + tick (setup_preproc_env.sh):
    python -I build_chunks_split.py --work-dir ".../work" --name A1 --scheme within_event
Keluaran: <work>/chunks/<name>/<scheme>/{chunk_train,chunk_val,chunk_test}.pkl, metadata.json, split_summary.json
"""
import argparse
import collections
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I tidak menambahkannya
import numpy as np  # noqa: E402
from common import EADRO_PREPROCESS  # noqa: E402

FAULT_TYPES = ["cpu_load", "network_delay", "network_loss"]
SPLITS = ["train", "val", "test"]

parser = argparse.ArgumentParser()
parser.add_argument("--work-dir", required=True)
parser.add_argument("--name", required=True)
parser.add_argument("--scheme", required=True, choices=["within_event", "leave_event_out", "random_original"])
parser.add_argument("--chunk-lenth", type=int, default=10)
parser.add_argument("--test-ratio", type=float, default=0.3, help="random_original saja (default align.py: 0.3)")
parser.add_argument("--split-seed", type=int, default=0, help="random_original saja: seed pengacakan jendela")
args = parser.parse_args()

work = os.path.abspath(args.work_dir)
parsed = os.path.join(work, "preprocess", "parsed_data", args.name)
out_dir = os.path.join(work, "chunks", args.name, args.scheme)
os.makedirs(out_dir, exist_ok=True)
os.chdir(os.path.join(work, "preprocess"))  # Eadro: ./parsed_data/<name>

sys.path.insert(0, EADRO_PREPROCESS)
sys.argv = ["align.py", "--name", args.name]  # align.py memanggil parse_args() saat di-import
import align  # noqa: E402

info = align.Info("trainticket")
L = args.chunk_lenth
with open(os.path.join(parsed, "manifest.json")) as f:
    manifest = json.load(f)


def split_rule(scheme, kind, is_test_event):
    """Daftar (batas_atas_posisi_relatif, id_split) untuk satu wilayah."""
    if scheme == "within_event":
        return [(0.5, 0), (0.6, 1), (1.0 + 1e-9, 2)]
    if is_test_event:
        return [(1.0 + 1e-9, 2)]
    return [(0.85, 0), (1.0 + 1e-9, 1)]


# leave_event_out: jenis fault yang jadi test untuk tiap service; run tanpa fault terakhir jadi test
test_type = {nid: FAULT_TYPES[nid % 3] for nid in range(info.node_num)}
last_nofault = max((m["idx"] for m in manifest if m["kind"] == "no_fault"), default=None)

buckets = {s: {} for s in SPLITS}
stats = {s: collections.Counter() for s in SPLITS}
per_node = {s: collections.Counter() for s in SPLITS}
per_type = {s: collections.Counter() for s in SPLITS}
dropped = 0
test_events = []
event_logs_dim = None

for m in manifest:
    idx = m["idx"]
    with open(os.path.join(parsed, "records{}.json".format(idx))) as f:
        rec = json.load(f)
    intervals, labels = align.get_basic(info, str(idx), name=args.name, chunk_lenth=L)
    n_win = len(intervals)
    starts = np.array([s for s, _ in intervals])
    start, end = rec["start"], rec["end"]
    labels = np.array(labels)

    # wilayah (detik inklusif) per kejadian; run tanpa fault = satu wilayah
    faults = rec["faults"]
    territories = []  # (lo, hi, kejadian atau None)
    if not faults:
        territories.append((start, end, None))
    else:
        cuts = [start - 1] + [(faults[k - 1]["e"] + faults[k]["s"]) // 2 for k in range(1, len(faults))] + [end]
        for k, fl in enumerate(faults):
            territories.append((cuts[k] + 1, cuts[k + 1], fl))

    sec_split = np.full(end - start + 1, -1, dtype=np.int8)
    ttype = {}
    for lo, hi, fl in territories:
        if fl is None:
            is_test = idx == last_nofault
            kind = "no_fault"
        else:
            nid = info.service2nid[fl["service"]]
            is_test = fl["type"] == test_type[nid]
            kind = fl["type"]
            if is_test and args.scheme == "leave_event_out":
                test_events.append((fl["service"], fl["type"]))
        rule = split_rule(args.scheme, kind, is_test)
        n = hi - lo + 1
        for t in range(lo, hi + 1):
            pos = (t - lo) / n
            sec_split[t - start] = next(sid for bound, sid in rule if pos < bound)
        ttype[(lo, hi)] = kind

    # satu jendela dipakai hanya jika semua detiknya berlabel split yang sama
    view = np.lib.stride_tricks.sliding_window_view(sec_split, L)  # (end-start+1-L+1, L)
    win_split = np.where(view.min(axis=1) == view.max(axis=1), view[:, 0], -1)[:n_win]
    if args.scheme == "random_original":
        win_split = np.zeros(n_win, dtype=np.int8)  # semua ke "train" dulu; diacak ke train/test setelah loop
    assert len(win_split) == n_win

    # tipe fault per jendela (untuk statistik)
    win_type = np.array(["normal"] * n_win, dtype=object)
    for fl in faults:
        mask = labels == info.service2nid[fl["service"]]
        win_type[mask & (starts <= fl["e"]) & (starts + L - 1 >= fl["s"])] = fl["type"]

    cdir = os.path.join(work, "chunks", args.name, str(idx))
    with open(os.path.join(cdir, "traces.pkl"), "rb") as f:
        traces = pickle.load(f)["latency"]
    with open(os.path.join(cdir, "metrics.pkl"), "rb") as f:
        metrics = pickle.load(f)
    with open(os.path.join(cdir, "logs.pkl"), "rb") as f:
        logs = pickle.load(f)
    event_logs_dim = logs.shape[-1]
    assert len(traces) == len(metrics) == len(logs) == n_win

    for w in range(n_win):
        sid = int(win_split[w])
        if sid < 0:
            dropped += 1
            continue
        sp = SPLITS[sid]
        culprit = int(labels[w])
        buckets[sp]["{:02d}_{}".format(idx, int(starts[w]))] = {
            "traces": traces[w].astype(np.float32), "metrics": metrics[w].astype(np.float32),
            "logs": logs[w].astype(np.float32), "culprit": culprit,
            "run": idx, "start": int(starts[w]), "fault_type": str(win_type[w]),
        }
    print("run {:2d} ({:8s}): {:5d} jendela, dibuang(purge) kumulatif: {}".format(idx, m["kind"], n_win, dropped), flush=True)

if args.scheme == "random_original":
    # seperti align.split_chunks: acak urutan, train = int((1-r)*n) pertama, test = int(r*n) berikutnya
    pool = buckets["train"]
    keys = sorted(pool)
    perm = np.random.default_rng(args.split_seed).permutation(len(keys))
    n_train, n_test = int((1 - args.test_ratio) * len(keys)), int(args.test_ratio * len(keys))
    buckets["train"] = {keys[p]: pool[keys[p]] for p in perm[:n_train]}
    buckets["test"] = {keys[p]: pool[keys[p]] for p in perm[n_train:n_train + n_test]}
    buckets["val"] = buckets["test"]  # epoch dipilih pakai test, seperti kode asli
    assert not set(buckets["train"]) & set(buckets["test"])
    del pool

for sp in SPLITS:
    for ch in buckets[sp].values():
        culprit = ch["culprit"]
        stats[sp]["faulty" if culprit >= 0 else "normal"] += 1
        if culprit >= 0:
            per_node[sp][culprit] += 1
        per_type[sp][ch["fault_type"]] += 1

for sp in SPLITS:
    with open(os.path.join(out_dir, "chunk_{}.pkl".format(sp)), "wb") as fw:
        pickle.dump(buckets[sp], fw, protocol=4)

meta = dict(info.metadata)
n_unique = len(set().union(*buckets.values()))  # random_original: val = test, jangan dihitung dua kali
meta.update({"chunk_lenth": L, "chunk_num": n_unique, "edges": info.edges,
             "event_num": int(event_logs_dim), "scheme": args.scheme,
             "split_seed": args.split_seed if args.scheme == "random_original" else None})
with open(os.path.join(out_dir, "metadata.json"), "w") as fw:
    json.dump(meta, fw, indent=2)

total = n_unique
print("\nSkema {} | jendela dipakai: {} | dibuang karena melintasi batas split: {}".format(args.scheme, total, dropped))
print("{:6s} {:>8s} {:>8s} {:>8s} {:>8s}  {}".format("split", "jendela", "faulty", "normal", "%faulty", "per jenis (jendela)"))
for sp in SPLITS:
    n = len(buckets[sp])
    print("{:6s} {:8d} {:8d} {:8d} {:7.1f}%  {}".format(
        sp, n, stats[sp]["faulty"], stats[sp]["normal"], 100 * stats[sp]["faulty"] / max(n, 1),
        dict(sorted(per_type[sp].items()))))
missing = {sp: [info.service_names[n] for n in range(info.node_num) if per_node[sp][n] == 0] for sp in SPLITS}
print("\nJendela faulty per node (min / median / max) dan node yang TIDAK punya contoh sama sekali:")
for sp in SPLITS:
    c = [per_node[sp][n] for n in range(info.node_num)]
    print("  {:6s} {:5d} / {:5.0f} / {:5d} | node tanpa contoh: {}".format(sp, min(c), float(np.median(c)), max(c), missing[sp] or "-"))
if args.scheme == "leave_event_out":
    print("\nKejadian yang disisihkan untuk test: {} (per jenis: {})".format(
        len(test_events), dict(collections.Counter(t for _, t in test_events))))
with open(os.path.join(out_dir, "split_summary.json"), "w") as fw:
    json.dump({"scheme": args.scheme, "dropped": dropped,
               "splits": {sp: {"windows": len(buckets[sp]), **dict(stats[sp]), "by_type": dict(per_type[sp]),
                               "faulty_per_node": {info.service_names[n]: per_node[sp][n] for n in range(info.node_num)}}
                          for sp in SPLITS}}, fw, indent=2)
print("\nDitulis ke", out_dir)
