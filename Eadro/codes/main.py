from torch.utils.data import Dataset, DataLoader
import torch
import dgl
class chunkDataset(Dataset): #[node_num, T, else]
    # Features are stacked into one tensor per source and the graph is only built per batch (see make_collate),
    # instead of keeping one DGLGraph object per chunk in memory.
    def __init__(self, chunks, node_num, edges):
        chunk_ids = list(chunks.keys())
        self.idx2id = dict(enumerate(chunk_ids))
        self.graph = dgl.graph(edges, num_nodes=node_num)
        self.logs = torch.from_numpy(np.stack([chunks[i]["logs"] for i in chunk_ids])).float()
        self.metrics = torch.from_numpy(np.stack([chunks[i]["metrics"] for i in chunk_ids])).float()
        self.traces = torch.from_numpy(np.stack([chunks[i]["traces"] for i in chunk_ids])).float()
        self.culprit = torch.tensor([chunks[i]["culprit"] for i in chunk_ids])
                
    def __len__(self):
        return len(self.culprit)
    def __getitem__(self, idx):
        return self.logs[idx], self.metrics[idx], self.traces[idx], self.culprit[idx]
    def __get_chunk_id__(self, idx):
        return self.idx2id[idx]

from utils import *
from base import BaseModel, SELECT_METRICS
from model import FUSIONS

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--random_seed", default=42, type=int)

### Training params
parser.add_argument("--gpu", default=True, type=lambda x: x.lower() == "true")
parser.add_argument("--epoches", default=50, type=int)
parser.add_argument("--batch_size", default=256, type=int)
parser.add_argument("--lr", default=0.001, type=float)
parser.add_argument("--patience", default=10, type=int)
parser.add_argument("--eval_every", default=5, type=int, help="evaluate on the validation set when (epoch+1) is a multiple of this")
parser.add_argument("--select_metric", default="combo", choices=list(SELECT_METRICS), help="validation criterion that selects the epoch")

##### Fuse params
parser.add_argument("--self_attn", default=True, type=lambda x: x.lower() == "true")
parser.add_argument("--fusion", default="concat_glu", choices=FUSIONS, help="how the three sources are fused")
parser.add_argument("--fuse_dim", default=128, type=int)
parser.add_argument("--alpha", default=0.5, type=float)
parser.add_argument("--locate_hiddens", default=[64], type=int, nargs='+')
parser.add_argument("--detect_hiddens", default=[64], type=int, nargs='+')

##### Source params
parser.add_argument("--log_dim", default=16, type=int)
parser.add_argument("--trace_kernel_sizes", default=[2], type=int, nargs='+')
parser.add_argument("--trace_hiddens", default=[64], type=int, nargs='+')
parser.add_argument("--metric_kernel_sizes", default=[2], type=int, nargs='+')
parser.add_argument("--metric_hiddens", default=[64], type=int, nargs='+')
parser.add_argument("--graph_hiddens", default=[64], type=int, nargs='+')
parser.add_argument("--attn_head", default=4, type=int, help="For gat or gat-v2")
parser.add_argument("--activation", default=0.2, type=float, help="use LeakyReLU, shoule be in (0,1)")

##### Data params
parser.add_argument("--data", type=str, required=True)
parser.add_argument("--result_dir", default="../result/")

params = vars(parser.parse_args())

import logging
def get_device(gpu):
    if gpu and torch.cuda.is_available():
        logging.info("Using GPU...")
        return torch.device("cuda")
    logging.info("Using CPU...")
    return torch.device("cpu")
    

def make_collate(graph):
    def collate(data):
        logs, metrics, traces, labels = map(torch.stack, zip(*data))
        batched_graph = dgl.batch([graph] * len(data))
        # [bz, node_num, ...] --> [bz*node_num, ...], the node order of dgl.batch
        batched_graph.ndata["logs"] = logs.flatten(0, 1)
        batched_graph.ndata["metrics"] = metrics.flatten(0, 1)
        batched_graph.ndata["traces"] = traces.flatten(0, 1)
        return batched_graph, labels
    return collate

def log_efficiency(model, dl, device, n_batches=4):
    """Parameters, inference time (forward pass only, batches prepared beforehand) and peak memory, for the efficiency comparison."""
    import resource, time
    enc = model.model.encoder
    n_total = sum(p.numel() for p in model.model.parameters())
    n_fuse = sum(p.numel() for n, p in enc.named_parameters() if n.startswith(("fuse.", "fusion_module.")))
    batches = []
    for i, (graph, label) in enumerate(dl):
        if i >= n_batches: break
        batches.append((graph.to(device), label))
    model.model.eval()
    with torch.no_grad():
        model.model.forward(*batches[0]) # warm-up
        start = time.time()
        for graph, label in batches: model.model.forward(graph, label)
        elapsed = time.time() - start
    n_windows = sum(g.batch_size for g, _ in batches)
    logging.info("Efficiency -- params_total: {}, params_fusion: {}, infer_ms_per_window: {:.4f}, peak_rss_mb: {:.0f}".format(
        n_total, n_fuse, 1000 * elapsed / n_windows, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024))

def run(evaluation_epoch=10):
    data_dir = os.path.join("../chunks", params["data"])

    metadata = read_json(os.path.join(data_dir, "metadata.json"))
    event_num, node_num, metric_num =  metadata["event_num"], metadata["node_num"], metadata["metric_num"]
    edges = tuple(metadata["edges"]) # (src_nids, dst_nids), written by preprocess/align.py
    params["chunk_lenth"] = metadata["chunk_lenth"]

    hash_id = dump_params(params)
    params["hash_id"] = hash_id
    seed_everything(params["random_seed"])
    device = get_device(params["gpu"])

    train_chunks, val_chunks, test_chunks = load_chunks(data_dir)

    train_data = chunkDataset(train_chunks, node_num, edges)
    val_data = chunkDataset(val_chunks, node_num, edges)
    test_data = chunkDataset(test_chunks, node_num, edges)
    del train_chunks, val_chunks, test_chunks # the features now live in the dataset tensors

    collate = make_collate(train_data.graph)
    train_dl = DataLoader(train_data, batch_size=params["batch_size"], shuffle=True, collate_fn=collate, pin_memory=True)
    val_dl = DataLoader(val_data, batch_size=params["batch_size"], shuffle=False, collate_fn=collate, pin_memory=True)
    test_dl = DataLoader(test_data, batch_size=params["batch_size"], shuffle=False, collate_fn=collate, pin_memory=True)

    model = BaseModel(event_num, metric_num, node_num, device, **params)
    scores, converge = model.fit(train_dl, val_dl, test_dl, evaluation_epoch=params["eval_every"])
    log_efficiency(model, val_dl, device)

    dump_scores(params["result_dir"], hash_id, scores, converge)
    logging.info("Current hash_id {}".format(hash_id))

if "__main__" == __name__:
    run()
