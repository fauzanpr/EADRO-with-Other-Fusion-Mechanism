"""Langkah 2c-i: parse logs.json (baris teks) menjadi templates.json + logs{idx}.csv untuk Eadro.

Format yang dibaca single_process.deal_logs:
    templates.json : daftar template event (satu file global untuk dataset; id event = posisi + 1, id 0 = 'Unseen')
    logs{idx}.csv  : kolom timestamp (detik epoch, int), service, event (string template)

Cara kerja:
  1. Header Spring Boot diurai: '<tgl> <jam>.<ms>  <LEVEL> <pid> --- [<thread>] <logger> : <isi>'.
     Waktu di logs.json = waktu label/metrics + 8 jam (SPAN_TZ_SHIFT_S); tiap run diperiksa ulang.
  2. Drain (paket drain3) pada <isi> pesan, dengan masking JWT / UUID / hex panjang / angka.
     Dua tahap: tahap 1 membangun cluster dari SEMUA baris SEMUA run (urut deterministik), tahap 2 memetakan ulang
     tiap baris ke template akhir (match), supaya template tidak berubah-ubah menurut urutan data.
  3. Semua baris dipertahankan, termasuk log 'Span reported' dari Jaeger (±40% baris; bagian dari data asli).

Pakai (Python dengan drain3):
    python -I build_logs.py --data-dir ".../TT Dataset/data" --out-dir ".../parsed_data/A1" [--nofault-root ...]
"""
import argparse
import collections
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I tidak menambahkannya
import pandas as pd  # noqa: E402
from drain3 import TemplateMiner  # noqa: E402
from drain3.masking import MaskingInstruction  # noqa: E402
from drain3.template_miner_config import TemplateMinerConfig  # noqa: E402

from common import SPAN_TZ_SHIFT_S, Info, all_runs  # noqa: E402

HEADER = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d{3}\s+(\w+)\s+(\d+)\s+---\s+\[(.*?)\]\s+(\S+)\s*:\s?(.*)$")
CANDIDATE_SHIFTS_H = [-16, -8, 0, 8, 16]
DRAIN_SIM_TH, DRAIN_DEPTH = 0.4, 4  # default drain3

MASKS = [  # urutan penting: yang spesifik dulu
    (r"eyJ[\w-]+\.[\w-]+\.[\w-]+", "JWT"),
    (r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "UUID"),
    (r"\b[0-9a-fA-F]{12,}\b", "HEX"),
    (r"\b\d+(\.\d+)?\b", "NUM"),
]


def make_miner():
    config = TemplateMinerConfig()
    config.drain_sim_th = DRAIN_SIM_TH
    config.drain_depth = DRAIN_DEPTH
    config.masking_instructions = [MaskingInstruction(p, m) for p, m in MASKS]
    return TemplateMiner(persistence_handler=None, config=config)


def parse_run(run_dir, info):
    """Return list of (epoch_naive, service, level, logger, isi) berurutan menurut Info.service_names lalu baris."""
    with open(os.path.join(run_dir, "logs.json")) as f:
        logs = json.load(f)
    foreign = [s for s in logs if s not in info.service2nid]
    assert not foreign, "service log tak dikenal: {}".format(foreign)
    rows = []
    for service in info.service_names:
        for line in logs.get(service, []):
            m = HEADER.match(line)
            assert m, "baris bukan format header Spring: {!r}".format(line[:120])
            t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
            rows.append((int(t), service, m.group(2), m.group(5), m.group(6)))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--out-dir", required=True, help="folder parsed_data/<nama>; harus sudah berisi records*.json")
    parser.add_argument("--nofault-root", nargs="*", default=[])
    args = parser.parse_args()

    info = Info("trainticket")
    runs = all_runs(args.data_dir, args.nofault_root)
    with open(os.path.join(args.out_dir, "manifest.json")) as f:
        manifest = json.load(f)
    assert [m["run"] for m in manifest] == [r[1] for r in runs], "daftar run tidak sama dengan manifest"

    parsed = []  # per run: rows dengan waktu sudah dikoreksi
    for idx, (kind, run_name, run_dir, _) in enumerate(runs):
        with open(os.path.join(args.out_dir, "records{}.json".format(idx))) as f:
            rec = json.load(f)
        rows = parse_run(run_dir, info)
        counts = {h: sum(rec["start"] <= r[0] - h * 3600 <= rec["end"] for r in rows) for h in CANDIDATE_SHIFTS_H}
        best = max(counts, key=counts.get)
        assert best * 3600 == SPAN_TZ_SHIFT_S and counts[best] == len(rows), \
            "run {}: pergeseran waktu logs tidak +8 jam / ada baris di luar jendela: {}".format(idx, counts)
        parsed.append([(t - SPAN_TZ_SHIFT_S, svc, lvl, lg, msg) for t, svc, lvl, lg, msg in rows])

    # --- Drain, tahap 1: bangun cluster dari semua baris
    miner = make_miner()
    for rows in parsed:
        for _, _, _, _, msg in rows:
            miner.add_log_message(msg)
    templates = []
    for cluster in sorted(miner.drain.clusters, key=lambda c: c.cluster_id):
        tpl = cluster.get_template()
        if tpl not in templates:  # dua cluster bisa berakhir dengan string template sama
            templates.append(tpl)
    with open(os.path.join(args.out_dir, "templates.json"), "w") as fw:
        json.dump(templates, fw, indent=2, ensure_ascii=False)

    # --- Drain, tahap 2: petakan ulang tiap baris ke template akhir, tulis logs{idx}.csv
    tpl_count = collections.Counter()
    per_run = []
    unseen = 0
    cache = {}
    for idx, rows in enumerate(parsed):
        out = []
        for t, svc, lvl, lg, msg in rows:
            if msg not in cache:
                cluster = miner.match(msg, full_search_strategy="fallback")
                cache[msg] = cluster.get_template() if cluster is not None else "Unseen"
            event = cache[msg]
            unseen += event == "Unseen"
            tpl_count[event] += 1
            out.append((t, svc, event))
        df = pd.DataFrame(out, columns=["timestamp", "service", "event"]).sort_values(["timestamp", "service"], kind="stable")
        df.to_csv(os.path.join(args.out_dir, "logs{}.csv".format(idx)), index=False)
        per_run.append({"idx": idx, "lines": len(df), "services_with_logs": int(df["service"].nunique())})

    n_lines = sum(tpl_count.values())
    with open(os.path.join(args.out_dir, "logs_summary.json"), "w") as fw:
        json.dump({"templates": len(templates), "lines": n_lines, "unseen": unseen, "runs": per_run,
                   "drain": {"sim_th": DRAIN_SIM_TH, "depth": DRAIN_DEPTH, "masks": [m for _, m in MASKS]}}, fw, indent=2)

    print("Baris: {} | template unik: {} | tak terpetakan (Unseen): {}".format(n_lines, len(templates), unseen))
    singles = sum(1 for t in templates if tpl_count[t] <= 2)
    print("Template dengan <=2 kemunculan: {} ({:.0f}%)".format(singles, 100 * singles / len(templates)))
    covered = sum(n for _, n in tpl_count.most_common(30))
    print("30 template teratas mencakup {:.1f}% baris\n".format(100 * covered / n_lines))
    print("Template terbanyak:")
    for tpl, n in tpl_count.most_common(25):
        print("  {:6d}  {}".format(n, tpl[:140]))
    print("\nPer run:")
    for r in per_run:
        print("  idx {:2d}: {:6d} baris, {} service punya log".format(r["idx"], r["lines"], r["services_with_logs"]))


if __name__ == "__main__":
    main()
