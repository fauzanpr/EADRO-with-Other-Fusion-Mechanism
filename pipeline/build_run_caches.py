"""Langkah 3a: hitung cache per run (traces.pkl, metrics.pkl, logs.pkl) dengan fungsi ASLI Eadro.

align.get_chunks memakai ulang file ../chunks/<nama>/<idx>/{traces,metrics,logs}.pkl bila sudah ada, jadi komputasi mahal
(terutama Hawkes pada logs, ±70 ms/jendela) bisa dijalankan paralel per run di sini, lalu align.py tinggal merakit.

Harus dijalankan dengan Python 3.8 + tick (lihat setup_preproc_env.sh), satu proses per run:
    OMP_NUM_THREADS=1 python -I build_run_caches.py --work-dir ".../work" --name A1 --idx 4

Struktur yang dipakai Eadro (path relatif): <work>/preprocess/parsed_data/<name>/..., <work>/chunks/<name>/<idx>/...
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I tidak menambahkannya
from common import EADRO_PREPROCESS  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--work-dir", required=True)
parser.add_argument("--name", required=True, help="nama dataset, diawali 'A' (TrainTicket)")
parser.add_argument("--idx", required=True)
parser.add_argument("--chunk-lenth", type=int, default=10)
parser.add_argument("--force", action="store_true", help="hitung ulang walau cache sudah ada")
args = parser.parse_args()

work = os.path.abspath(args.work_dir)
pre_dir = os.path.join(work, "preprocess")
aim = os.path.join(work, "chunks", args.name, args.idx)
os.makedirs(aim, exist_ok=True)
os.chdir(pre_dir)  # Eadro: ./parsed_data/<name> dan ../chunks/<name>/<idx>

sys.path.insert(0, EADRO_PREPROCESS)
sys.argv = ["align.py", "--name", args.name]  # align.py memanggil parse_args() saat di-import
import align  # noqa: E402
import single_process  # noqa: E402

info = align.Info("trainticket")
L = args.chunk_lenth
intervals, labels = align.get_basic(info, args.idx, name=args.name, chunk_lenth=L)
print("run {}: {} jendela".format(args.idx, len(intervals)), flush=True)

jobs = [
    ("traces", lambda: single_process.deal_traces(intervals, info, args.idx, name=args.name, chunk_lenth=L)),
    ("metrics", lambda: single_process.deal_metrics(intervals, info, args.idx, name=args.name, chunk_lenth=L)),
    ("logs", lambda: single_process.deal_logs(intervals, info, args.idx, name=args.name)),
]
for key, fn in jobs:
    pkl = os.path.join(aim, key + ".pkl")
    if os.path.exists(pkl) and not args.force:
        print("run {}: {}.pkl sudah ada, lewati".format(args.idx, key), flush=True)
        continue
    t0 = time.time()
    fn()
    print("run {}: {}.pkl selesai dalam {:.0f}s".format(args.idx, key, time.time() - t0), flush=True)
