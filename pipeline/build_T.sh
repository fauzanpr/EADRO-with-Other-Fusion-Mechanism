#!/usr/bin/env bash
# Bangun data untuk SATU panjang jendela T, terpisah dari data T=10 (A1). Tiap T = dataset sendiri bernama A1_T<T>:
#   work/preprocess/parsed_data/A1_T<T>  -> symlink ke A1 (data mentah hasil parse tidak disalin)
#   work/chunks/A1_T<T>/<idx>/           cache per run (traces/metrics/logs), bergantung pada T
#   work/chunks/A1_T<T>/<skema>/         chunk train/val/test + metadata.json (berisi chunk_lenth=T)
# Data A1 (T=10) tidak disentuh. Tiap T bisa dibangun dan dilatih sendiri-sendiri, dalam urutan apa pun.
#
# Pakai:  pipeline/build_T.sh <T> [skema ...]          (default skema: within_event)
# Contoh: pipeline/build_T.sh 5
#         pipeline/build_T.sh 30 within_event leave_event_out
# Lalu latih:  DATA_NAME=A1_T5 pipeline/run_grid.sh within_event 15 "42 7 123" "concat_glu"
#
# Env: JOBS=4        jumlah run yang dibangun paralel (satu proses per run, OMP_NUM_THREADS=1)
#      DRY=1         hanya cetak perintah, tidak menjalankan apa pun
#      FORCE=1       bangun ulang chunk skema walau sudah ada (cache per run yang sudah ada tetap dipakai ulang)
#      PREPROC_PY=   python 3.8 + tick (default work/envs/preproc38/bin/python)
# Log per run: work/build_logs/A1_T<T>_run<idx>.log. Bagian paling lama adalah fitur log (Hawkes) di tiap run.
# Aman diulang: build_run_caches.py melewati cache yang sudah ada, jadi bila terhenti cukup jalankan lagi.
set -euo pipefail

T="${1:?pakai: build_T.sh <T> [skema ...]}"
shift
SCHEMES=("$@"); [[ ${#SCHEMES[@]} -gt 0 ]] || SCHEMES=(within_event)
[[ "$T" =~ ^[0-9]+$ && "$T" -ge 2 ]] || { echo "T harus bilangan bulat >= 2" >&2; exit 1; }
for s in "${SCHEMES[@]}"; do
  [[ "$s" == within_event || "$s" == leave_event_out ]] || { echo "skema tidak dikenal: $s" >&2; exit 1; }
done
[[ "$T" -ne 10 ]] || { echo "T=10 sudah ada sebagai A1 (jangan dibangun ulang sebagai A1_T10)." >&2; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY="${PREPROC_PY:-$ROOT/work/envs/preproc38/bin/python}"
JOBS="${JOBS:-4}"
NAME="A1_T${T}"
PD="$ROOT/work/preprocess/parsed_data"
LOGS="$ROOT/work/build_logs"

[[ -x "$PY" ]] || { echo "Python preprocessing tidak ditemukan: $PY (pipeline/setup_preproc_env.sh)" >&2; exit 1; }
[[ -d "$PD/A1" ]] || { echo "Data parse tidak ditemukan: $PD/A1" >&2; exit 1; }

mapfile -t IDX < <(find "$PD/A1/" -maxdepth 1 -name 'records*.json' | sed -E 's/.*records([0-9]+)\.json/\1/' | sort -n)
[[ ${#IDX[@]} -gt 0 ]] || { echo "Tidak ada records*.json di $PD/A1" >&2; exit 1; }

echo "T=$T | nama=$NAME | skema=${SCHEMES[*]} | run=${#IDX[@]} (idx ${IDX[0]}..${IDX[-1]}) | paralel=$JOBS | $(date '+%F %T')"
if [[ "${DRY:-0}" == 1 ]]; then
  echo "[DRY] ln -s A1 $PD/$NAME   (bila belum ada)"
  for i in "${IDX[@]}"; do
    echo "[DRY] OMP_NUM_THREADS=1 $PY -I $HERE/build_run_caches.py --work-dir $ROOT/work --name $NAME --idx $i --chunk-lenth $T  > $LOGS/${NAME}_run${i}.log"
  done
  for s in "${SCHEMES[@]}"; do
    echo "[DRY] $PY -I $HERE/build_chunks_split.py --work-dir $ROOT/work --name $NAME --scheme $s --chunk-lenth $T"
  done
  exit 0
fi

mkdir -p "$LOGS"
[[ -e "$PD/$NAME" ]] || ln -s A1 "$PD/$NAME"

export ROOT PY NAME T LOGS HERE
build_one() {
  local i="$1" log="$LOGS/${NAME}_run${1}.log"
  echo "  [$(date '+%T')] run $i mulai"
  if OMP_NUM_THREADS=1 "$PY" -I "$HERE/build_run_caches.py" --work-dir "$ROOT/work" --name "$NAME" --idx "$i" \
        --chunk-lenth "$T" > "$log" 2>&1; then
    echo "  [$(date '+%T')] run $i selesai"
  else
    echo "  [$(date '+%T')] run $i GAGAL, lihat $log"; return 1
  fi
}
export -f build_one

echo "== 1/2 cache per run (traces, metrics, logs) =="
printf '%s\n' "${IDX[@]}" | xargs -P "$JOBS" -I{} bash -c 'build_one {}' \
  || { echo "Ada run yang gagal; periksa log di $LOGS lalu jalankan ulang perintah yang sama." >&2; exit 1; }

echo "== 2/2 rakit chunk + bagi train/val/test =="
for s in "${SCHEMES[@]}"; do
  if [[ -f "$ROOT/work/chunks/$NAME/$s/chunk_train.pkl" && "${FORCE:-0}" != 1 ]]; then
    echo "  $s: sudah ada, lewati (FORCE=1 untuk membangun ulang)"; continue
  fi
  echo "  [$(date '+%T')] $s"
  "$PY" -I "$HERE/build_chunks_split.py" --work-dir "$ROOT/work" --name "$NAME" --scheme "$s" --chunk-lenth "$T" \
      2>&1 | tail -n 4
  [[ -f "$ROOT/work/chunks/$NAME/$s/chunk_train.pkl" ]] || { echo "$s: chunk tidak terbentuk" >&2; exit 1; }
done

echo "== selesai $(date '+%F %T') =="
for s in "${SCHEMES[@]}"; do
  "$PY" -I -c "
import json,sys
d='$ROOT/work/chunks/$NAME/$s/'
m=json.load(open(d+'metadata.json')); s=json.load(open(d+'split_summary.json'))
print('$NAME/$s: chunk_lenth=%s | ' % m['chunk_lenth'] + ' | '.join('%s %d (gangguan %d, normal %d)' % (k, v['windows'], v['faulty'], v['normal']) for k, v in s['splits'].items()), '| dibuang(purge):', s['dropped'])"
done
echo "Latih:  DATA_NAME=$NAME $ROOT/pipeline/run_grid.sh <skema> 15 \"42 7 123\" \"concat_glu\""
