#!/usr/bin/env bash
# Environment Python 3.8 untuk langkah preprocessing yang butuh `tick` (fitur Hawkes pada logs: single_process.deal_logs,
# yang dipanggil align.py). `tick` tidak terpasang di Python 3.12, dan tick 0.7.0.1 hanya punya wheel untuk
# cp36/cp37/cp38 (tidak ada cp39). Python sistem tidak diubah: uv mengunduh Python 3.8 mandiri ke folder env.
#
# Versi mengikuti Eadro/requirements.txt (hanya yang dipakai preprocessing: numpy, pandas, tick).
# Pakai:  setup_preproc_env.sh <folder_env>     (butuh `uv` di PATH: pip install uv)
set -euo pipefail

ENV_DIR="${1:?pakai: setup_preproc_env.sh <folder_env>}"
command -v uv >/dev/null || { echo "uv tidak ditemukan di PATH; pasang dengan: pip install uv" >&2; exit 1; }

uv venv --python 3.8 "$ENV_DIR"
uv pip install --python "$ENV_DIR/bin/python" "numpy==1.21.5" "pandas==1.4.2" "tick==0.7.0.1"
"$ENV_DIR/bin/python" -c "import numpy, pandas; from tick.hawkes import HawkesADM4; print('tick OK | numpy', numpy.__version__, '| pandas', pandas.__version__)"
