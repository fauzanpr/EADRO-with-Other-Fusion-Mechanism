"""Langkah 2a: bangun records{idx}.json dan metrics{idx}/<service>.csv untuk Eadro.

Format yang diharapkan Eadro/codes/preprocess (align.get_basic dan single_process.deal_metrics):
    records{idx}.json : {"start": int, "end": int, "faults": [{"s": int, "e": int, "service": str}]}
    metrics{idx}/<service>.csv : kolom timestamp + Info.metric_names, tepat 1 baris per detik

Konvensi waktu fault (inklusif, dalam slot 1 detik [t, t+1)):
    s = floor(start), e = ceil(start + duration) - 1
    -> sebuah slot dianggap faulty jika bersinggungan dengan interval fault [start, start+duration).

Run tanpa fault dimasukkan dengan faults = [] (rentang diambil dari metrics). idx: run berfault dulu, lalu tanpa fault.

Pakai:
    python -I build_records_metrics.py --data-dir ".../TT Dataset/data" --out-dir ".../work/preprocess/parsed_data/A1" \
        [--nofault-root ".../work/raw_nofault/<arsip1>" ".../work/raw_nofault/<arsip2>" ...]
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I tidak menambahkannya
import pandas as pd  # noqa: E402
from common import Info, all_runs, container_to_service  # noqa: E402


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_metrics_range(run_dir, info):
    """Validasi 27 CSV metrics satu run; return (ts_pertama, ts_terakhir, jumlah_baris)."""
    firsts, lasts, rows = set(), set(), set()
    files = sorted(os.listdir(os.path.join(run_dir, "metrics")))
    assert files == sorted(s + ".csv" for s in info.service_names), "daftar service metrics != Info.service_names"
    for fn in files:
        df = pd.read_csv(os.path.join(run_dir, "metrics", fn))
        assert list(df.columns) == ["timestamp"] + info.metric_names, fn + ": kolom tidak sesuai"
        assert (df["timestamp"].diff().dropna() == 1).all(), fn + ": ada celah/duplikat timestamp"
        assert not df.isna().any().any(), fn + ": ada NaN"
        firsts.add(int(df["timestamp"].iloc[0])); lasts.add(int(df["timestamp"].iloc[-1])); rows.add(len(df))
    assert len(firsts) == len(lasts) == len(rows) == 1, "rentang waktu beda antar service"
    return firsts.pop(), lasts.pop(), rows.pop()


def build_records(meta, run_name, start, end, info):
    """meta: isi fault JSON, atau None untuk run tanpa fault."""
    faults = []
    for f in (meta["faults"] if meta else []):
        service = container_to_service(f["name"])
        assert service in info.service2nid, "service tak dikenal: " + service
        faults.append({
            "s": math.floor(f["start"]),
            "e": math.ceil(f["start"] + f["duration"]) - 1,
            "service": service,
            "type": f["fault"],  # tidak dipakai Eadro; berguna untuk analisis per jenis fault
        })
    faults.sort(key=lambda x: x["s"])
    for a, b in zip(faults, faults[1:]):
        assert a["e"] < b["s"], "fault tumpang tindih: {} dan {}".format(a, b)
    if faults:
        assert start <= faults[0]["s"] and faults[-1]["e"] <= end, "fault di luar rentang metrics"
    return {"run": run_name, "start": start, "end": end, "faults": faults}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True, help="folder 'data' berisi TT.<run>/ dan TT.fault-<run>.json")
    parser.add_argument("--out-dir", required=True, help="folder parsed_data/<nama dataset>, mis. .../parsed_data/A1")
    parser.add_argument("--nofault-root", nargs="*", default=[], help="folder hasil ekstrak arsip run tanpa fault")
    args = parser.parse_args()

    info = Info("trainticket")
    runs = all_runs(args.data_dir, args.nofault_root)
    os.makedirs(args.out_dir, exist_ok=True)

    manifest = []
    print("{:>3s} {:8s} {:36s} {:>10s} {:>10s} {:>6s} {:>6s}  {}".format(
        "idx", "jenis", "run", "start", "end", "detik", "fault", "service (urut injeksi)"))
    for idx, (kind, run_name, run_dir, fault_json) in enumerate(runs):
        meta = None
        if fault_json:
            with open(fault_json) as f:
                meta = json.load(f)
        start, end, n_rows = read_metrics_range(run_dir, info)
        records = build_records(meta, run_name, start, end, info)

        with open(os.path.join(args.out_dir, "records{}.json".format(idx)), "w") as fw:
            json.dump(records, fw, indent=2)

        aim = os.path.join(args.out_dir, "metrics{}".format(idx))
        os.makedirs(aim, exist_ok=True)
        for service in info.service_names:
            src = os.path.join(run_dir, "metrics", service + ".csv")
            dst = os.path.join(aim, service + ".csv")
            shutil.copyfile(src, dst)
            assert sha256(src) == sha256(dst), "salinan rusak: " + dst  # metrics disalin apa adanya

        seq = []
        for f in records["faults"]:
            short = f["service"][len("ts-"):-len("-service")]
            if not seq or seq[-1][0] != short:
                seq.append([short, 0])
            seq[-1][1] += 1
        print("{:3d} {:8s} {:36s} {:10d} {:10d} {:6d} {:6d}  {}".format(
            idx, kind, run_name[len("TT."):], start, end, n_rows, len(records["faults"]),
            ", ".join("{}x{}".format(s, n) for s, n in seq) or "-"))
        manifest.append({"idx": idx, "kind": kind, "run": run_name, "start": start, "end": end, "rows": n_rows,
                         "faults": len(records["faults"])})

    with open(os.path.join(args.out_dir, "manifest.json"), "w") as fw:
        json.dump(manifest, fw, indent=2)
    print("\nSelesai: {} run -> {}".format(len(runs), args.out_dir))


if __name__ == "__main__":
    main()
