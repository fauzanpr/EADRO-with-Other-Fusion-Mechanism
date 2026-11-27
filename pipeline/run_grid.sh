#!/usr/bin/env bash
# Jalankan beberapa training berurutan: setiap fusion x setiap seed, pada satu skema data.
#
# Pakai:  pipeline/run_grid.sh <skema> <epoch> "<daftar seed>" "<daftar fusion>" [argumen tambahan untuk main.py ...]
# Contoh: pipeline/run_grid.sh leave_event_out 20 "42 7 123" "concat_glu concat_fc sum attn lmf"
#         DATA_NAME=A1_T5 pipeline/run_grid.sh within_event 15 "42 7 123" "concat_glu"     (data T=5, lihat build_T.sh)
#
# Urutan: seed di luar, fusion di dalam. Jika proses terhenti di tengah jalan, semua fusion sudah punya jumlah seed
# yang sama (selisih paling banyak satu seed), sehingga hasil sebagian tetap bisa dibandingkan.
# Run yang sudah selesai dicatat di work/result/grid_selesai.txt dan dilewati saat skrip dijalankan ulang.
# Agar tetap jalan walau terminal ditutup:
#   nohup pipeline/run_grid.sh leave_event_out 20 "42 7 123" "concat_glu concat_fc sum attn lmf" > grid_leo.out 2>&1 &
set -uo pipefail

SCHEME="${1:?pakai: run_grid.sh <skema> <epoch> \"<seed ...>\" \"<fusion ...>\" [argumen main.py ...]}"
EPOCHS="${2:?epoch}"
SEEDS="${3:?daftar seed, mis. \"42 7 123\"}"
FUSIONS="${4:?daftar fusion, mis. \"concat_glu attn\"}"
shift 4

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
RESULT_DIR="${RESULT_DIR:-$ROOT/work/result}"
export DATA_NAME="${DATA_NAME:-A1}"   # diteruskan ke run_train.sh; A1 = T=10, data T lain: A1_T<T> (pipeline/build_T.sh)
mkdir -p "$RESULT_DIR"
DONE="$RESULT_DIR/grid_selesai.txt"
touch "$DONE"

total=$(( $(wc -w <<<"$SEEDS") * $(wc -w <<<"$FUSIONS") )); n=0
for seed in $SEEDS; do
  for fusion in $FUSIONS; do
    n=$((n + 1))
    key="$SCHEME $EPOCHS $fusion $seed $*"
    # nama dataset ikut dalam kunci (selain A1, agar catatan lama tetap berlaku); tanpa ini run T lain dianggap sudah selesai
    [[ "$DATA_NAME" == "A1" ]] || key="$DATA_NAME $key"
    if grep -qxF "$key" "$DONE"; then echo "[$n/$total] lewati (sudah selesai): $key"; continue; fi
    echo "[$n/$total] mulai $(date '+%F %T'): fusion=$fusion seed=$seed"
    "$HERE/run_train.sh" "$SCHEME" "$seed" "$EPOCHS" --fusion "$fusion" "$@" 2>&1 | grep --line-buffered -E "^Skema|Best result|Efficiency|Current hash_id|Traceback|Error"
    status=${PIPESTATUS[0]}   # status run_train.sh, bukan grep
    if [[ $status -eq 0 ]]; then echo "$key" >> "$DONE"; else echo "  GAGAL (kode $status): $key"; fi
  done
done
echo "Selesai $(date '+%F %T')"
