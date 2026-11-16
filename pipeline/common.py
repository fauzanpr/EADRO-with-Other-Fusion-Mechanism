"""Helper bersama pipeline: TT Dataset mentah -> parsed_data yang dibaca Eadro/codes/preprocess."""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EADRO_PREPROCESS = os.path.normpath(os.path.join(HERE, "..", "Eadro", "codes", "preprocess"))
sys.path.insert(0, EADRO_PREPROCESS)
from util import Info  # noqa: E402  (daftar 27 service TrainTicket, nama kolom metrics, edges)

# Waktu di spans.json (dan logs.json) = waktu label/metrics + 8 jam.
# Terbukti pada 9 run berfault: hanya shift +8 jam yang menjatuhkan span ke dalam jendela run, dan hanya dengan
# shift itu latensi menuju service yang di-fault melonjak tepat di dalam jendela fault (lihat build_traces.py).
SPAN_TZ_SHIFT_S = 8 * 3600


def discover_runs(data_dir):
    """Run berfault, urut kronologis (nama run berformat ISO, jadi urut leksikografis = urut waktu).

    Return list of (run_name, run_dir, fault_json_path); idx run = posisinya di list ini.
    """
    runs = []
    for run_dir in sorted(glob.glob(os.path.join(data_dir, "TT.2*"))):
        if not os.path.isdir(run_dir):
            continue
        name = os.path.basename(run_dir)
        fault_json = os.path.join(data_dir, "TT.fault-" + name[len("TT."):] + ".json")
        assert os.path.exists(fault_json), "fault JSON tidak ada: " + fault_json
        runs.append((name, run_dir, fault_json))
    return runs


def discover_nofault_runs(roots):
    """Run tanpa fault dari folder hasil ekstrak arsip (tiap root = satu arsip, folder run bisa bersarang).

    Run diidentifikasi sebagai folder 'TT.2*' yang berisi spans.json dan metrics/. Return list of (run_name, run_dir, None).
    """
    runs = {}
    for root in roots:
        for cur, dirs, files in os.walk(root):
            if os.path.basename(cur).startswith("TT.2") and "spans.json" in files and "metrics" in dirs:
                runs[os.path.basename(cur)] = cur
    return [(name, runs[name], None) for name in sorted(runs)]


def all_runs(data_dir, nofault_roots=()):
    """Daftar run lengkap: [(kind, run_name, run_dir, fault_json)], berfault dulu lalu tanpa fault.

    Urutan ini menentukan idx (records{idx}.json, metrics{idx}/, traces{idx}.json, ...) di seluruh pipeline.
    """
    runs = [("fault",) + r for r in discover_runs(data_dir)]
    runs += [("no_fault",) + r for r in discover_nofault_runs(nofault_roots)]
    return runs


def container_to_service(container):
    """'dockercomposemanifests_ts-basic-service_1' -> 'ts-basic-service'"""
    return container.replace("dockercomposemanifests_", "", 1).rsplit("_", 1)[0]
