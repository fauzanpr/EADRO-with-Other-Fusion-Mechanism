"""Rekap hasil training per grup: rata-rata ± sd antar seed pada epoch terpilih.

Pakai:  work/envs/train312/bin/python pipeline/rekap_seed.py work/result

Grup = data + jumlah epoch + fusion + kriteria pilih epoch + eval_every, supaya run dengan pengaturan berbeda tidak
tercampur. Run lama yang params.json-nya belum punya kunci fusion/select_metric/eval_every dianggap
concat_glu / HR@1 / 10 (perilaku kode sebelum opsi itu ada). Run uji cepat (< 5 epoch) dilewati.
Hanya percobaan terakhir di tiap running.log yang dibaca (log dengan hash sama di-append).
"""
import json, os, re, sys, glob, statistics as st
root = sys.argv[1]
KEYS = ["F1(std)", "Rec(std)", "Pre(std)", "HR@1(std)", "HR@3(std)", "HR@5(std)", "ndcg@3(std)", "ndcg@5(std)", "F1", "HR@1", "HR@3", "HR@5"]
TABLE_KEYS = ["F1(std)", "Pre(std)", "Rec(std)", "HR@1(std)", "HR@3(std)", "ndcg@3(std)"]
EFF_KEYS = ["params_fusion", "params_total", "infer_ms_per_window", "peak_rss_mb"]

def parse_line(s):
    return {k: float(v) for k, v in re.findall(r"([A-Za-z0-9@()_]+): ([0-9.]+)", s.split(" -- ", 1)[1])}

def mean_sd(xs, fmt="{:.3f}"):
    if len(xs) < 2: return fmt.format(xs[0]) if xs else "-"
    return (fmt + " ± " + fmt).format(st.mean(xs), st.stdev(xs))

rows = []
for d in sorted(glob.glob(os.path.join(root, "*/params.json"))):
    p = json.load(open(d)); run = os.path.basename(os.path.dirname(d))
    if p.get("epoches", 0) < 5: continue  # lewati uji cepat
    lines = open(os.path.join(os.path.dirname(d), "running.log")).read().splitlines()
    starts = [i for i, l in enumerate(lines) if "Using CPU" in l or "Using GPU" in l]
    lines = lines[starts[-1]:] if starts else lines
    ep, vals, tests, eff, ep_secs = 0, {}, {}, {}, []
    for l in lines:
        m = re.search(r"Epoch (\d+)/\d+, training loss: [0-9.]+ \[([0-9.]+)s\]", l)
        if m: ep = int(m.group(1)); ep_secs.append(float(m.group(2)))
        if " Val -- " in l: vals[ep] = parse_line(l)
        if " Test -- " in l: tests[ep] = parse_line(l)
        if "Efficiency -- " in l: eff = parse_line(l)
    best = re.findall(r"Best result got at epoch (\d+) with validation (\S+): ([0-9.]+)", "\n".join(lines))
    status = "selesai" if best else "berjalan (epoch %d)" % ep
    fusion = p.get("fusion", "concat_glu")
    data = "{} ({} ep)".format(p["data"], p["epoches"])
    setting = "pilih {} | eval tiap {}".format(p.get("select_metric", "HR@1"), p.get("eval_every", 10))
    rows.append(dict(run=run, data=data, fusion=fusion, setting=setting, seed=p["random_seed"], vals=vals, tests=tests,
                     best=best[-1] if best else None, status=status, ep=ep, eff=eff,
                     sec_per_epoch=st.mean(ep_secs) if ep_secs else None))

# 1) rincian per run
for r in rows:
    print("{} | {} | {} | seed {} | {} | terpilih: {}".format(r["run"], r["data"], r["fusion"], r["seed"], r["status"], r["best"]))
    for e in sorted(r["vals"]):
        v = r["vals"][e]; t = r["tests"].get(e)
        print("   ep{:2d} Val combo {:.4f} HR@1asli {:.4f} F1s {:.3f} Pre {:.3f} HR1s {:.3f} | Test: {}".format(
            e, (v["F1(std)"] + v["HR@1(std)"]) / 2, v["HR@1"], v["F1(std)"], v["Pre(std)"], v["HR@1(std)"],
            ("F1s {:.3f} Pre {:.3f} HR1s {:.3f}".format(t["F1(std)"], t["Pre(std)"], t["HR@1(std)"]) if t else "-- (tidak dihitung)")))
print()

# 2) rata-rata ± sd per grup (data + fusion + pengaturan), di epoch terpilih
groups = sorted({(r["data"], r["fusion"], r["setting"]) for r in rows})
summary = {}
for g in groups:
    done = [r for r in rows if (r["data"], r["fusion"], r["setting"]) == g and r["best"] and int(r["best"][0]) in r["tests"]]
    if not done: continue
    summary[g] = done
    if len(done) < 2: continue
    print("== {} | {} | {} | {} seed selesai {} | epoch terpilih {} ==".format(
        g[0], g[1], g[2], len(done), [r["seed"] for r in done], [r["best"][0] for r in done]))
    for k in KEYS:
        xs = [r["tests"][int(r["best"][0])][k] for r in done]
        print("   {:12s} mean {:.4f}  sd {:.4f}  | per seed {}".format(k, st.mean(xs), st.stdev(xs), ["%.3f" % x for x in xs]))
print()

# 3) tabel perbandingan fusion: satu tabel per (data, pengaturan), satu baris per fusion
for data, setting in sorted({(g[0], g[2]) for g in summary}):
    fus = [g for g in summary if g[0] == data and g[2] == setting]
    if len(fus) < 2: continue  # belum ada pembanding
    print("#### Perbandingan fusion: {} | {} (Test, epoch terpilih, mean ± sd antar seed)".format(data, setting))
    head = ["fusion", "n"] + TABLE_KEYS + ["params_fusion", "params_total", "ms/jendela", "RSS MB", "s/epoch"]
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for g in sorted(fus, key=lambda g: g[1]):
        done = summary[g]
        cells = [g[1], str(len(done))]
        cells += [mean_sd([r["tests"][int(r["best"][0])][k] for r in done]) for k in TABLE_KEYS]
        effs = [r["eff"] for r in done if r["eff"]]
        cells += ["{:.0f}".format(effs[0]["params_fusion"]) if effs else "-",
                  "{:.0f}".format(effs[0]["params_total"]) if effs else "-",
                  mean_sd([e["infer_ms_per_window"] for e in effs], "{:.3f}") if effs else "-",
                  mean_sd([e["peak_rss_mb"] for e in effs], "{:.0f}") if effs else "-",
                  mean_sd([r["sec_per_epoch"] for r in done if r["sec_per_epoch"]], "{:.1f}")]
        print("| " + " | ".join(cells) + " |")
    print()
