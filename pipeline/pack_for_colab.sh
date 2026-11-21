#!/usr/bin/env bash
# Kemas kode + data chunk untuk diunggah ke Google Drive, lalu dipakai pipeline/colab_train.ipynb.
#
# Pakai:  pipeline/pack_for_colab.sh <DATA_NAME ...>
# Contoh: pipeline/pack_for_colab.sh A1                 (T=10, kedua skema)
#         pipeline/pack_for_colab.sh A1_T40 A1_T50      (data T lain; dibuat oleh pipeline/build_T.sh)
#
# Hasil di work/colab_pack/ (ganti lewat OUT=...):
#   eadro_code.tar              Eadro/codes + pipeline (kecil; selalu dibuat ulang)
#   eadro_data_<NAME>.tar       chunk_{train,val,test}.pkl + metadata.json + split_summary.json tiap skema yang ada
#   SHA256SUMS_<NAME>.txt       sidik jari tiap file chunk; notebook memeriksanya setelah ekstrak, sebagai bukti bahwa data di
#                               Colab sama persis dengan data di laptop (relevan untuk keabsahan perbandingan)
# Cache per run (folder 0..11 di work/chunks/<NAME>/) TIDAK ikut: hanya dibutuhkan untuk membangun chunk, bukan untuk training.
# Unggah semua file di OUT ke satu folder Drive (mis. MyDrive/eadro/), lalu jalankan notebook.
#   DRY=1  hanya cetak apa yang akan dikemas.
set -euo pipefail

[[ $# -ge 1 ]] || { echo "pakai: pack_for_colab.sh <DATA_NAME ...>" >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="${OUT:-$ROOT/work/colab_pack}"
SCHEMES=(within_event leave_event_out)
FILES=(chunk_train.pkl chunk_val.pkl chunk_test.pkl metadata.json split_summary.json)

run() { if [[ "${DRY:-0}" == 1 ]]; then echo "[DRY] $*"; else "$@"; fi; }
run mkdir -p "$OUT"

echo "== kode =="
run tar -C "$ROOT" -cf "$OUT/eadro_code.tar" --exclude=__pycache__ --exclude='*.pyc' Eadro/codes pipeline

for NAME in "$@"; do
    echo "== data $NAME =="
    LIST=()
    for s in "${SCHEMES[@]}"; do
        d="work/chunks/$NAME/$s"
        if [[ -f "$ROOT/$d/chunk_train.pkl" ]]; then
            for f in "${FILES[@]}"; do LIST+=("$d/$f"); done
            echo "  skema $s: ada"
        else
            echo "  skema $s: tidak ada, dilewati"
        fi
    done
    [[ ${#LIST[@]} -gt 0 ]] || { echo "tidak ada chunk untuk '$NAME' di $ROOT/work/chunks/" >&2; exit 1; }

    if [[ "${DRY:-0}" == 1 ]]; then
        printf '[DRY]   %s\n' "${LIST[@]}"
        echo "[DRY] tar -> $OUT/eadro_data_$NAME.tar, sha256 -> $OUT/SHA256SUMS_$NAME.txt"
        continue
    fi
    ( cd "$ROOT" && printf '%s\n' "${LIST[@]}" | grep '\.pkl$' | xargs -d '\n' sha256sum ) > "$OUT/SHA256SUMS_$NAME.txt"
    tar -C "$ROOT" -cf "$OUT/eadro_data_$NAME.tar" "${LIST[@]}"
    echo "  -> $(du -h "$OUT/eadro_data_$NAME.tar" | cut -f1)  $OUT/eadro_data_$NAME.tar"
done

echo "== selesai. Unggah isi $OUT ke Google Drive (mis. MyDrive/eadro/) =="
[[ "${DRY:-0}" == 1 ]] || ls -lh "$OUT"
