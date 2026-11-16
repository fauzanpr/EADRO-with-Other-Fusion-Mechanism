#!/usr/bin/env bash
# Environment Python untuk TRAINING model EADRO (CPU). Terpisah dari preproc38 (yang hanya untuk `tick`).
#
# Versi bukan pin requirements.txt repo (torch 1.12.1 / dgl 0.9.1 butuh Python lama), tetapi kombinasi yang sudah
# teruji di Python 3.12: DGL 2.1.0 hanya mendukung torch <= 2.2.1; torch 2.2.1 butuh numpy < 2;
# DGL 2.1.0 butuh setuptools < 70, torchdata 0.7.1 (memuat datapipes), pyyaml, pydantic.
# ipykernel + matplotlib + pandas ikut dipasang supaya env yang sama bisa dipakai sebagai kernel notebook (membaca hasil).
#
# Pakai:  pipeline/setup_train_env.sh [folder_env]      (default: work/envs/train312)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="${1:-$HERE/../work/envs/train312}"

python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), sys.version' 2>/dev/null \
    || echo "peringatan: python3 bukan 3.12; versi paket di bawah hanya diuji di 3.12" >&2

python3 -m venv "$ENV_DIR"
pip() { "$ENV_DIR/bin/python" -m pip "$@"; }  # fungsi, bukan variabel: path proyek mengandung spasi
pip install --quiet --upgrade pip
pip install --quiet "setuptools<70" wheel
pip install --quiet "torch==2.2.1" --index-url https://download.pytorch.org/whl/cpu
pip install --quiet "numpy<2" "torchdata==0.7.1" "dgl==2.1.0" \
    "scikit-learn==1.5.2" "pyyaml" "pydantic" "pandas" "scipy" "tqdm" "psutil" \
    "ipykernel" "matplotlib" \
    -f https://data.dgl.ai/wheels/torch-2.2/repo.html

DGLBACKEND=pytorch "$ENV_DIR/bin/python" -W ignore - <<'EOF'
import torch, dgl, numpy, sklearn
g = dgl.graph(([0, 1], [1, 2]), num_nodes=3)
print("OK | torch", torch.__version__, "| dgl", dgl.__version__, "| numpy", numpy.__version__,
      "| sklearn", sklearn.__version__, "| graf uji:", g.num_nodes(), "node,", g.num_edges(), "sisi")
EOF
echo "Env siap di: $ENV_DIR"
