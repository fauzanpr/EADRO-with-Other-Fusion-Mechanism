#!/usr/bin/env bash
# Jalankan satu training EADRO pada data kita.
#
# Pakai:  pipeline/run_train.sh <skema> [seed=42] [epoch=50] [argumen tambahan untuk main.py ...]
#         <skema> = within_event | leave_event_out
# Contoh: pipeline/run_train.sh within_event 42
#         pipeline/run_train.sh within_event 42 1          (uji cepat: 1 epoch, ±3 menit)
#         pipeline/run_train.sh leave_event_out 7 50 --lr 0.0005
#
# Hasil: work/result/<hash_id>/{params.json, running.log, model.ckpt}; ringkasan tiap run ditambahkan ke
#        work/result/experiments.txt. Folder hasil dapat diganti lewat RESULT_DIR=... Env lewat TRAIN_PY=....
# Data  : default work/chunks/A1 (T=10). Untuk T lain:  DATA_NAME=A1_T5 pipeline/run_train.sh within_event 42
# Agar tetap jalan walau terminal ditutup:  nohup pipeline/run_train.sh within_event 42 > train_we42.out 2>&1 &
set -euo pipefail

SCHEME="${1:?pakai: run_train.sh <within_event|leave_event_out> [seed] [epoch] [argumen main.py ...]}"
SEED="${2:-42}"
EPOCHS="${3:-50}"
shift $(( $# < 3 ? $# : 3 ))

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY="${TRAIN_PY:-$ROOT/work/envs/train312/bin/python}"
RESULT_DIR="${RESULT_DIR:-$ROOT/work/result}"
DATA_NAME="${DATA_NAME:-A1}"   # A1 = T=10 (asli); data T lain dibuat oleh pipeline/build_T.sh dengan nama A1_T<T>

[[ -x "$PY" ]] || { echo "Python training tidak ditemukan: $PY  (jalankan pipeline/setup_train_env.sh dulu)" >&2; exit 1; }
[[ -f "$ROOT/work/chunks/$DATA_NAME/$SCHEME/chunk_train.pkl" ]] || { echo "Data tidak ada untuk '$DATA_NAME/$SCHEME'" >&2; exit 1; }
mkdir -p "$RESULT_DIR"

export DGLBACKEND=pytorch PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/Eadro/codes"
cd "$ROOT/work/preprocess"   # main.py membaca data lewat path relatif ../chunks/<data>
echo "Skema=$SCHEME data=$DATA_NAME seed=$SEED epoch=$EPOCHS | hasil -> $RESULT_DIR | $(date '+%F %T')"
exec "$PY" -W ignore "$ROOT/Eadro/codes/main.py" --data "$DATA_NAME/$SCHEME" --random_seed "$SEED" --epoches "$EPOCHS" \
    --result_dir "$RESULT_DIR/" "$@"
