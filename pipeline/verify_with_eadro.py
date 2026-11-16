"""Verifikasi parsed_data dengan menjalankan kode ASLI Eadro, bukan tiruannya.

Yang dipanggil: align.get_basic (jendela + label), single_process.deal_metrics (jendela metrics + z-score, termasuk
assert bentuk (chunk_lenth, metric_num) di setiap jendela) dan single_process.deal_traces (jendela latensi + z-score).
Modul `tick` di-stub karena hanya dipakai untuk fitur Hawkes pada logs (langkah berikutnya).

Selain tidak crash, tensor trace dicocokkan dengan hitungan independen dari traces{idx}.json: jumlah entri
(jendela, node, slot) yang berisi span harus persis sama.

Hasil tulis (chunks .pkl) ditaruh di direktori sementara supaya tidak meninggalkan cache basi di work/chunks.

Pakai:  python -I verify_with_eadro.py --parsed-data ".../work/preprocess/parsed_data/A1"
"""
import argparse
import json
import os
import sys
import tempfile
import time
import types
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I tidak menambahkannya
import numpy as np  # noqa: E402
from common import EADRO_PREPROCESS  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--parsed-data", required=True, help="folder parsed_data/<nama>, nama harus diawali 'A' (TrainTicket)")
parser.add_argument("--chunk-lenth", type=int, default=10)
parser.add_argument("--runs", type=int, nargs="*", help="idx run yang dicek (default: semua)")
args = parser.parse_args()

parsed = os.path.abspath(args.parsed_data)
name = os.path.basename(parsed)
n_runs = len([f for f in os.listdir(parsed) if f.startswith("records")])
runs = args.runs if args.runs else list(range(n_runs))

# stub tick: single_process.py meng-import HawkesADM4 di level modul
tick, hawkes = types.ModuleType("tick"), types.ModuleType("tick.hawkes")
hawkes.HawkesADM4 = None
sys.modules["tick"], sys.modules["tick.hawkes"] = tick, hawkes

sys.path.insert(0, EADRO_PREPROCESS)
sys.argv = ["align.py", "--name", name]  # align.py memanggil parse_args() saat di-import
import align  # noqa: E402
import single_process  # noqa: E402


def expected_nonempty(traces_json, node, start, end, L):
    """Hitungan independen: jumlah entri (jendela, slot) yang berisi span untuk satu node (dst)."""
    seconds = set()
    for ts, edges in traces_json.items():
        if any(int(k.split("-")[-1]) == node for k in edges):
            seconds.add(int(ts))
    # jendela mulai s di range(start, end-L+1); detik t ada di jendela s jika s <= t <= s+L-1
    total = 0
    for t in seconds:
        lo, hi = max(start, t - L + 1), min(t, end - L)
        total += max(0, hi - lo + 1)
    return total


with tempfile.TemporaryDirectory() as tmp:
    # Eadro memakai path relatif: ./parsed_data/<name> dan ../chunks/<name>/<idx>
    os.makedirs(os.path.join(tmp, "preprocess", "parsed_data"))
    os.symlink(parsed, os.path.join(tmp, "preprocess", "parsed_data", name))
    for idx in runs:
        os.makedirs(os.path.join(tmp, "chunks", name, str(idx)))
    os.chdir(os.path.join(tmp, "preprocess"))

    info = align.Info("trainticket")
    L = args.chunk_lenth
    total, faulty, per_node = 0, 0, Counter()
    win_with_trace = np.zeros(info.node_num)  # jumlah jendela per node yang berisi >= 1 span
    print("\n{:>3s} {:>8s} {:>8s} {:>8s} {:>22s} {:>8s} {:>8s} {:>10s} {:>7s}".format(
        "idx", "jendela", "faulty", "normal", "metrics.shape", "met(s)", "trace(s)", "node+trace", "max|z|"))
    for idx in runs:
        with open(os.path.join(parsed, "records{}.json".format(idx))) as f:
            rec = json.load(f)
        with open(os.path.join(parsed, "traces{}.json".format(idx))) as f:
            traces_json = json.load(f)

        intervals, labels = align.get_basic(info, str(idx), name=name, chunk_lenth=L)
        n_win = len(intervals)
        t0 = time.time()
        metrics = single_process.deal_metrics(intervals, info, str(idx), name=name, chunk_lenth=L)
        t_met = time.time() - t0
        t0 = time.time()
        traces = single_process.deal_traces(intervals, info, str(idx), name=name, chunk_lenth=L)
        t_tr = time.time() - t0
        lat = traces["latency"]

        n_fault = sum(l != -1 for l in labels)
        assert metrics.shape == (n_win, info.node_num, L, len(info.metric_names)), metrics.shape
        assert lat.shape == (n_win, info.node_num, L, 1), lat.shape
        assert np.isfinite(metrics).all() and np.isfinite(lat).all(), "NaN/inf pada metrics atau traces"

        covered = 0
        for node in range(info.node_num):
            arr = lat[:, node, :, 0]
            expect = expected_nonempty(traces_json, node, rec["start"], rec["end"], L)
            if expect == 0:
                assert np.abs(arr).max() == 0, "node tanpa span harus nol semua"
                continue
            covered += 1
            # slot kosong bernilai (0-mean)/std = nilai minimum (latensi > 0), jadi slot berisi = entri di atas minimum
            got = int((arr > arr.min() + 1e-9).sum())
            assert got == expect, "node {}: tensor {} != hitungan independen {}".format(info.service_names[node], got, expect)
            win_with_trace[node] += int((arr > arr.min() + 1e-9).any(axis=1).sum())
        print("{:3d} {:8d} {:8d} {:8d} {:>22s} {:8.1f} {:8.1f} {:10d} {:7.1f}".format(
            idx, n_win, n_fault, n_win - n_fault, str(metrics.shape), t_met, t_tr, covered, np.abs(lat).max()))
        total += n_win; faulty += n_fault
        per_node.update(l for l in labels if l != -1)

    print("\nTotal jendela: {} | faulty: {} ({:.1f}%) | normal: {} ({:.1f}%)".format(
        total, faulty, 100 * faulty / total, total - faulty, 100 * (total - faulty) / total))
    counts = [per_node.get(n, 0) for n in range(info.node_num)]
    print("Jendela faulty per node (culprit): min={} median={:.0f} max={} | node tanpa label: {}".format(
        min(counts), float(np.median(counts)), max(counts), [info.service_names[n] for n in range(info.node_num) if counts[n] == 0]))
    if len(runs) == n_runs:
        assert all(c > 0 for c in counts), "ada node yang tidak pernah jadi culprit"

    print("\nKepadatan trace: % jendela (dari {}) yang berisi >= 1 span, per node".format(total))
    for node in np.argsort(-win_with_trace):
        if win_with_trace[node] > 0:
            print("  {:32s} {:5.1f}%".format(info.service_names[node], 100 * win_with_trace[node] / total))
    print("  node tanpa span sama sekali: {}/{}".format(int((win_with_trace == 0).sum()), info.node_num))
    print("\nSemua pengecekan lolos.")
