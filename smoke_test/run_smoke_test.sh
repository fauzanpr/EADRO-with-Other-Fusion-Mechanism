#!/usr/bin/env bash
# Smoke test Eadro (model.py + base.py + main.py asli) pada chunk SINTETIS. Bukan data TT.
#
# Memeriksa: jalur forward/backward/evaluasi/simpan checkpoint tidak crash, loss turun,
# dan HR@1 pada chunk uji berada di atas acak (1/27 = 0.037).
#
# Python yang dipakai harus punya (kombinasi yang teruji di Python 3.12; DGL 2.1.0 hanya
# mendukung torch <= 2.2.1):
#   torch==2.2.1 (CPU), dgl==2.1.0, torchdata==0.7.1, numpy<2, pandas<2.3,
#   scikit-learn<1.6, scipy<1.14, pyyaml, pydantic, setuptools<70
#
# Pakai:  PY=/path/ke/venv/bin/python ./run_smoke_test.sh [jumlah_chunk=8000] [epoch=30] [argumen main.py ...]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CODES="$HERE/../Eadro/codes"
PY="${PY:-python3}"
CHUNKS="${1:-8000}"
EPOCHES="${2:-30}"
shift $(( $# < 2 ? $# : 2 ))   # sisanya diteruskan ke main.py, mis. --fusion attn

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/codes" "$WORK/chunks"

export PYTHONDONTWRITEBYTECODE=1 DGLBACKEND=pytorch
"$PY" "$HERE/make_smoke_chunks.py" "$CODES" "$WORK/chunks/SMOKE" node "$CHUNKS"

# main.py memakai path relatif (../chunks, ../result), jadi jalankan dari direktori kerja sementara
cd "$WORK/codes"
"$PY" -W ignore "$CODES/main.py" --data SMOKE --gpu false --epoches "$EPOCHES" --patience "$EPOCHES" "$@"
