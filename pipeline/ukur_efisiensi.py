"""Ukur biaya model EADRO TANPA data nyata: parameter, FLOPs, elemen aktivasi, latensi inferensi, waktu satu langkah latih.

Mengapa data acak: untuk lapisan yang dipakai model (Conv1d, BatchNorm, Linear, bmm, GATv2, pooling) biaya hitungnya tidak
bergantung pada isi tensor, hanya pada bentuknya. Bentuk diambil dari metadata chunk (jumlah node, metrik, event, sisi graf).
Hasil TIDAK menyentuh akurasi; ini hanya biaya.

Pakai (env training, mis. work/envs/train312):
    python -I pipeline/ukur_efisiensi.py --mode T        --out work/efisiensi_T.json
    python -I pipeline/ukur_efisiensi.py --mode fusion   --out work/efisiensi_fusion.json

Yang diukur (per jendela, satu jendela = satu sampel 27 node x T detik):
  params_total, params_fusion  seperti log_efficiency di Eadro/codes/main.py
  flops                        hanya matmul/konvolusi (torch FlopCounterMode, 1 FLOP perkalian-tambah = 2). Operasi elementwise
                               (BatchNorm, ReLU, tanh, softmax) dan kernel graf DGL TIDAK terhitung.
  flops_temporal               bagian flops di cabang trace + metric (satu-satunya bagian yang bergantung T)
  act_elems                    jumlah elemen keluaran semua modul daun (proxy memori aktivasi), bukan puncak memori sebenarnya
  lat_b1_ms_t{4,1}             latensi forward satu jendela (batch 1), median dan p95 dari banyak ulangan, thread bawaan torch (4 di laptop ini) atau 1 thread
  ms_b256                      ms per jendela, batch 256, thread bawaan, hanya model (encoder + dua kepala, tanpa loss)
  ms_b256_repo                 sama tetapi memanggil model.forward penuh seperti log_efficiency (termasuk loss dan loop Python)
  train_ms_per_window          satu langkah latih (forward + backward + Adam), batch 256, thread bawaan
Seluruh pengukuran diulang --rounds kali dan dilaporkan median antar-ronde, dengan min-maks antar-ronde.
"""
import argparse, json, os, statistics as st, sys, time

import torch
import dgl

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "Eadro", "codes"))
from model import MainModel, FUSIONS  # noqa: E402
from torch.utils.flop_counter import FlopCounterMode  # noqa: E402

KW = dict(log_dim=16, fuse_dim=128, alpha=0.5, trace_kernel_sizes=[2], trace_hiddens=[64], metric_kernel_sizes=[2],
          metric_hiddens=[64], graph_hiddens=[64], attn_head=4, activation=0.2, self_attn=True,
          locate_hiddens=[64], detect_hiddens=[64])


def meta_for(T):
    name = "A1" if T == 10 else "A1_T%d" % T
    for scheme in ("within_event", "leave_event_out"):
        p = os.path.join(ROOT, "work", "chunks", name, scheme, "metadata.json")
        if os.path.exists(p):
            return json.load(open(p))
    sys.exit("metadata chunk untuk T=%d tidak ditemukan" % T)


def build(T, fusion, meta):
    torch.manual_seed(0)
    N, M, E = meta["node_num"], meta["metric_num"], meta["event_num"]
    model = MainModel(E, M, N, torch.device("cpu"), fusion=fusion, chunk_lenth=T, **KW)
    return model


def make_graph(meta, T, bs):
    N, M, E = meta["node_num"], meta["metric_num"], meta["event_num"]
    g = dgl.graph(tuple(meta["edges"]), num_nodes=N)
    bg = dgl.batch([g] * bs)
    bg.ndata["logs"] = torch.rand(bs, N, E).flatten(0, 1)
    bg.ndata["metrics"] = torch.rand(bs, N, T, M).flatten(0, 1)
    bg.ndata["traces"] = torch.rand(bs, N, T, 1).flatten(0, 1)
    return bg


def net_forward(model, graph):
    """encoder + dua kepala (tanpa loss, tanpa loop Python per sampel)"""
    emb = model.encoder(graph)
    return model.localizer(emb), model.detecter(emb)


def flops_of(fn):
    with FlopCounterMode(display=False) as fc:
        fn()
    return fc.get_total_flops()


def act_elems(model, graph):
    total = [0]
    hooks = []
    for m in model.encoder.modules():
        if len(list(m.children())) == 0:
            hooks.append(m.register_forward_hook(lambda mod, i, o: total.__setitem__(0, total[0] + (o.numel() if torch.is_tensor(o) else 0))))
    with torch.no_grad():
        net_forward(model, graph)
    for h in hooks:
        h.remove()
    return total[0]


def timed(fn, warm, reps):
    for _ in range(warm):
        fn()
    xs = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    return xs


def measure_once(T, fusion, meta, threads_default):
    model = build(T, fusion, meta)
    out = {"T": T, "fusion": fusion}
    out["params_total"] = sum(p.numel() for p in model.parameters())
    out["params_fusion"] = sum(p.numel() for n, p in model.encoder.named_parameters() if n.startswith(("fuse.", "fusion_module.")))
    model.eval()
    g1 = make_graph(meta, T, 1)
    with torch.no_grad():
        out["flops"] = flops_of(lambda: net_forward(model, g1))
        out["flops_temporal"] = flops_of(lambda: model.encoder.trace_model(g1.ndata["traces"])) + \
                                flops_of(lambda: model.encoder.metric_model(g1.ndata["metrics"]))
    out["act_elems"] = act_elems(model, g1)

    with torch.no_grad():
        for th in (threads_default, 1):
            torch.set_num_threads(th)
            xs = timed(lambda: net_forward(model, g1), 20, 300)
            xs.sort()
            out["lat_b1_ms_t%d" % th] = st.median(xs)
            out["lat_b1_p95_t%d" % th] = xs[int(0.95 * len(xs)) - 1]
        torch.set_num_threads(threads_default)
        g256 = make_graph(meta, T, 256)
        lab = torch.randint(-1, meta["node_num"], (256,))
        out["ms_b256"] = st.median(timed(lambda: net_forward(model, g256), 4, 10)) / 256
        out["ms_b256_repo"] = st.median(timed(lambda: model.forward(g256, lab), 4, 10)) / 256

    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lab = torch.randint(-1, meta["node_num"], (256,))

    def step():
        opt.zero_grad()
        model.forward(g256, lab)["loss"].backward()
        opt.step()
    out["train_ms_per_window"] = st.median(timed(step, 3, 6)) / 256
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["T", "fusion"], required=True)
    ap.add_argument("--Ts", default="5,10,30,40,50,60")
    ap.add_argument("--fusion_Ts", default="10")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    th0 = torch.get_num_threads()
    if a.mode == "T":
        configs = [(int(t), "concat_glu") for t in a.Ts.split(",")]
    else:
        configs = [(int(t), f) for t in a.fusion_Ts.split(",") for f in FUSIONS]
    metas = {T: meta_for(T) for T, _ in configs}
    ref = metas[configs[0][0]]
    for T, m in metas.items():
        if m["edges"] != ref["edges"] or m["node_num"] != ref["node_num"] or m["metric_num"] != ref["metric_num"]:
            print("PERINGATAN: graf/jumlah node berbeda pada T=%d" % T)
    rounds = []
    for r in range(a.rounds):
        res = []
        for T, f in configs:
            res.append(measure_once(T, f, metas[T], th0))
            print("ronde %d  T=%d %-10s b1=%.2f ms  b256=%.3f ms  train=%.3f ms/jendela" % (r + 1, T, f, res[-1]["lat_b1_ms_t%d" % th0], res[-1]["ms_b256"], res[-1]["train_ms_per_window"]), flush=True)
        rounds.append(res)
    final = []
    for i, (T, f) in enumerate(configs):
        row = {"T": T, "fusion": f, "threads_default": th0, "rounds": a.rounds}
        for k in rounds[0][i]:
            if k in ("T", "fusion"):
                continue
            vals = [rounds[r][i][k] for r in range(a.rounds)]
            row[k] = st.median(vals)
            if isinstance(vals[0], float):
                row[k + "_min"], row[k + "_max"] = min(vals), max(vals)
        final.append(row)
    json.dump({"torch": torch.__version__, "dgl": dgl.__version__, "threads": th0, "rows": final}, open(a.out, "w"), indent=1)
    print("ditulis", a.out)


if __name__ == "__main__":
    main()
