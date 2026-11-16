"""Langkah 2b: bangun traces{idx}.json dari spans.json (Jaeger) untuk Eadro.

Format yang dibaca single_process.deal_traces:
    traces{idx}.json : {"<detik epoch>": {"<nid_caller>-<nid_callee>": [latensi_ms, ...]}}
    (latensi node = rata-rata latensi semua invokasi yang MENUJU node itu pada slot 1 detik tsb)

Atribusi, mengikuti paper (Sec. IV-C.3: "invocation latency ... average latency at a time slot for each callee"):
  - hanya client span (span.kind=client): durasi seluruh invokasi dari sisi pemanggil, sehingga delay/loss jaringan
    pada callee ikut terukur (server span tidak akan menangkapnya)
  - callee = host pada tag http.url; caller = process.serviceName milik span
  - waktu = detik mulai span, setelah dikurangi SPAN_TZ_SHIFT_S (8 jam); durasi mikrodetik -> milidetik
  - dedup per (traceID, spanID): spans.json memuat tiap span ±4x
  - hanya span di dalam [start, end] run (spans.json juga memuat span jauh di luar run)

Setiap run diperiksa ulang: pergeseran waktu harus tetap +8 jam (jumlah span di jendela run terbanyak pada +8 jam).

Pakai:
    python -I build_traces.py --data-dir ".../TT Dataset/data" --out-dir ".../parsed_data/A1" [--nofault-root ...]
"""
import argparse
import collections
import json
import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I tidak menambahkannya
from common import SPAN_TZ_SHIFT_S, Info, all_runs  # noqa: E402

CANDIDATE_SHIFTS_H = [-16, -8, 0, 8, 16]


def load_unique_spans(path):
    """Span unik: dict (traceID, spanID) -> (start_sec_float, durasi_us, kind, caller_service, callee_host)."""
    with open(path) as f:
        data = json.load(f)
    spans, n_rows = {}, 0
    for trace in data:
        procs = {pid: p["serviceName"] for pid, p in trace["processes"].items()}
        for sp in trace["spans"]:
            n_rows += 1
            key = (sp["traceID"], sp["spanID"])
            if key in spans:
                continue
            tags = {t["key"]: t["value"] for t in sp.get("tags", [])}
            kind = tags.get("span.kind")
            callee = urlparse(tags["http.url"]).hostname if kind == "client" and "http.url" in tags else None
            spans[key] = (sp["startTime"] / 1e6, sp["duration"], kind, procs.get(sp["processID"]), callee)
    return spans, n_rows


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
    assert [m["run"] for m in manifest] == [r[1] for r in runs], "daftar run tidak sama dengan manifest (jalankan build_records_metrics.py dulu)"

    totals = collections.Counter()
    callee_total = collections.Counter()
    callee_runs = collections.defaultdict(set)
    summary = []
    print("{:>3s} {:8s} {:>8s} {:>6s} {:>7s} {:>8s} {:>8s} {:>8s} {:>9s}  {}".format(
        "idx", "jenis", "baris", "unik", "dlmRun", "client", "dipakai", "detikAda", "drop", "alasan drop"))
    for idx, (kind, run_name, run_dir, _) in enumerate(runs):
        with open(os.path.join(args.out_dir, "records{}.json".format(idx))) as f:
            rec = json.load(f)
        start, end = rec["start"], rec["end"]
        spans, n_rows = load_unique_spans(os.path.join(run_dir, "spans.json"))

        counts = {h: sum(start <= v[0] - h * 3600 <= end for v in spans.values()) for h in CANDIDATE_SHIFTS_H}
        best = max(counts, key=counts.get)
        others = max(c for h, c in counts.items() if h != best)
        assert best * 3600 == SPAN_TZ_SHIFT_S, "run {}: pergeseran waktu terbaik {}h, bukan +8h: {}".format(idx, best, counts)
        assert others < 0.1 * counts[best], "run {}: pergeseran waktu ambigu: {}".format(idx, counts)

        traces = collections.defaultdict(lambda: collections.defaultdict(list))
        in_run = n_client = used = 0
        drops = collections.Counter()
        for st, dur, k, caller, callee in spans.values():
            t = int(st - SPAN_TZ_SHIFT_S)  # lantai ke detik (slot [t, t+1))
            if not (start <= t <= end):
                continue
            in_run += 1
            if k != "client":
                continue
            n_client += 1
            if callee is None:
                drops["tanpa http.url"] += 1
            elif callee not in info.service2nid:
                drops["callee bukan service TT: " + str(callee)] += 1
            elif caller not in info.service2nid:
                drops["caller bukan service TT: " + str(caller)] += 1
            else:
                dst = info.service2nid[callee]
                traces[str(t)]["{}-{}".format(info.service2nid[caller], dst)].append(round(dur / 1000.0, 3))
                used += 1
                callee_total[callee] += 1
                callee_runs[callee].add(idx)

        ordered = {t: dict(traces[t]) for t in sorted(traces, key=int)}
        with open(os.path.join(args.out_dir, "traces{}.json".format(idx)), "w") as fw:
            json.dump(ordered, fw)
        n_drop = sum(drops.values())
        print("{:3d} {:8s} {:8d} {:6d} {:7d} {:8d} {:8d} {:8d} {:9d}  {}".format(
            idx, kind, n_rows, len(spans), in_run, n_client, used, len(ordered), n_drop,
            "; ".join("{} x{}".format(k, v) for k, v in drops.items()) or "-"))
        summary.append({"idx": idx, "rows": n_rows, "unique": len(spans), "in_run": in_run, "client": n_client,
                        "used": used, "seconds_with_span": len(ordered), "run_seconds": end - start + 1,
                        "shift_check": {str(h): c for h, c in counts.items()}, "drops": dict(drops)})
        totals.update(rows=n_rows, unique=len(spans), used=used)

    with open(os.path.join(args.out_dir, "traces_summary.json"), "w") as fw:
        json.dump({"runs": summary, "callee_total": dict(callee_total),
                   "callee_runs": {k: sorted(v) for k, v in callee_runs.items()}}, fw, indent=2)

    print("\nTotal: {} baris -> {} span unik; {} client span dipakai".format(totals["rows"], totals["unique"], totals["used"]))
    print("\nCakupan modalitas trace per service (sebagai callee): jumlah client span, jumlah run yang punya >=1 span")
    for s in info.service_names:
        print("  {:34s} {:6d} span  {:2d}/{} run".format(s, callee_total.get(s, 0), len(callee_runs.get(s, ())), len(runs)))
    have = [s for s in info.service_names if callee_total.get(s, 0) > 0]
    print("\nService dengan >=1 span: {}/{} | tanpa span sama sekali: {}".format(
        len(have), info.node_num, [s for s in info.service_names if s not in have]))


if __name__ == "__main__":
    main()
