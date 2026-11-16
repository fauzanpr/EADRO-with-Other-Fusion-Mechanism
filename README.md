# Replikasi dan Eksperimen Fusion EADRO pada Train Ticket

Tugas kuliah APDM. Proyek ini mereplikasi **EADRO** (*An End-to-End Troubleshooting Framework for Microservices on Multi-source Data*, 2023) pada dataset **Train Ticket (TT)**, lalu membandingkan beberapa cara menggabungkan tiga sumber data (metrics, traces, logs), yang disebut *fusion*. Di paper, cara penggabungan ini tidak pernah dibandingkan dengan alternatif lain.

EADRO mengerjakan dua hal sekaligus pada sistem microservices:

1. **Deteksi anomali**: apakah sistem sedang bermasalah?
2. **Lokalisasi akar masalah**: kalau ya, service mana penyebabnya? (metrik HR@k dan NDCG@k)

## Isi repositori

| Path | Isi |
|---|---|
| `Eadro/` | Kode asli EADRO (hasil clone repo penulis), dengan perbaikan bug |
| `pipeline/` | Script buatan sendiri: preprocessing data mentah, pembagian data, training, dan pembacaan hasil |
| `smoke_test/` | Uji asap: menjalankan model dengan data buatan untuk memastikan kode tidak crash |
| `work/result/` | Hasil training: `params.json` dan `running.log` per run, `ringkasan_hasil.csv`, gambar |
| `work/build_logs/` | Log pembuatan data per run |
| `Report/` | Laporan eksperimen dan draf PPT progress (Markdown) |
| `*.ipynb` | Notebook EDA dan pembacaan hasil training |
| `Ringkasan_*.md`, `Penjelasan_Pekerjaan_EADRO.md` | Catatan dan penjelasan pekerjaan |

## Apa yang tidak ada di repositori

Ukuran dataset dan data olahannya terlalu besar untuk GitHub, jadi semua ini masuk `.gitignore`:

- `TT Dataset/` dan `TT Dataset.zip`
- `work/chunks/`, `work/preprocess/`, `work/raw_nofault/` (total sekitar 9 GB)
- `work/envs/` (virtualenv)
- File checkpoint model (`*.ckpt`) dan array/pickle (`*.npy`, `*.pkl`, dan sejenisnya)

Akibatnya, **membaca dan menganalisis hasil** bisa dilakukan di device mana pun (lihat bagian di bawah), tetapi **melatih ulang atau membangun data** butuh dataset mentah yang ditaruh manual.

## Menganalisis hasil (tanpa dataset)

Cukup `git clone`, lalu:

```bash
pip install pandas numpy matplotlib
python pipeline/baca_hasil.py          # tabel + gambar ke work/result/
python pipeline/rekap_seed.py work/result   # rata-rata ± sd antar seed
```

`baca_hasil.py` hanya membaca `running.log` dan `params.json`, lalu membuat `ringkasan_hasil.csv` dan gambar (kurva loss, HR@1 validasi, perbandingan fusion). Notebook `Hasil_Training.ipynb` memakai fungsi yang sama.

Laporan lengkap ada di `Report/`:

| Laporan | Isi |
|---|---|
| `Penjelasan_EDA_dan_Baseline.md` | Temuan data dan baseline pertama |
| `Temuan_Data_dan_Sweep_T.md` | Temuan data dan sweep panjang jendela T |
| `Laporan_Eksperimen_Seed.md` | Baseline 3 seed |
| `Laporan_Tingkat_A_Protokol_Asli.md` | Meniru protokol kode rilis, dan mengapa angkanya hampir sama dengan paper |
| `Laporan_Fusion_F1_vs_F2.md` | Perbandingan fusion |
| `Laporan_Efisiensi_F1.md` | Efisiensi (parameter, waktu inferensi, memori) |

## Menjalankan ulang dari awal

Butuh dataset TT mentah di `TT Dataset/` (struktur dan sumbernya mengikuti `Eadro/Readme.md`), `uv`, dan Python 3.12. Semua perintah dijalankan dari root repositori. Training memakai CPU saja.

### 1. Siapkan environment

```bash
pip install uv
pipeline/setup_preproc_env.sh work/envs/preproc38   # Python 3.8 + tick (fitur Hawkes pada logs)
pipeline/setup_train_env.sh                          # Python 3.12 + torch 2.2.1 + DGL 2.1.0 -> work/envs/train312
```

Dua environment dipisah karena `tick` hanya punya wheel untuk Python 3.6 sampai 3.8, sedangkan DGL dan torch yang dipakai butuh Python 3.12.

### 2. Bangun data

Data mentah diubah menjadi format yang diminta kode EADRO. Langkahnya: `build_records_metrics.py`, `build_traces.py`, `build_logs.py`, `build_run_caches.py`, lalu `build_chunks_split.py`. Untuk panjang jendela selain T=10, ada pembungkusnya:

```bash
pipeline/build_T.sh 5                                  # data T=5 -> work/chunks/A1_T5
pipeline/build_T.sh 30 within_event leave_event_out
```

Verifikasi hasilnya dengan `pipeline/verify_caches.py` dan `pipeline/verify_with_eadro.py`.

### 3. Latih

```bash
# satu run: <skema> [seed] [epoch] [argumen main.py]
pipeline/run_train.sh within_event 42 50
pipeline/run_train.sh leave_event_out 7 50 --fusion attn

# banyak run: setiap seed x setiap fusion
pipeline/run_grid.sh leave_event_out 20 "42 7 123" "concat_glu concat_fc sum attn lmf"

# data T lain
DATA_NAME=A1_T5 pipeline/run_grid.sh within_event 15 "42 7 123" "concat_glu"
```

Agar tetap jalan setelah terminal ditutup, awali dengan `nohup` dan akhiri dengan `&`. `run_grid.sh` mencatat run yang selesai di `work/result/grid_selesai.txt` dan melewatinya bila dijalankan ulang.

### 4. Skema pembagian data

| Skema | Arti |
|---|---|
| `within_event` | Tiap kejadian gangguan dipotong menurut waktu (50% awal train, 10% val, 40% akhir test). Tanpa kebocoran waktu |
| `leave_event_out` | Untuk tiap service, satu jenis gangguan sengaja disisihkan sebagai test |
| `random_original` | Tiruan pembagian acak di kode rilis EADRO. Bocor waktu, jadi hanya untuk perbandingan dengan paper |

### 5. Pilihan fusion

`concat_glu` (asli EADRO), `concat_fc`, `sum`, `attn`, `lmf`.

### 6. Diagnosis

Script berikut memuat `model.ckpt` dan data chunk, jadi hanya jalan di mesin yang punya keduanya:

```bash
work/envs/train312/bin/python -I pipeline/diagnose_alarm.py --run <hash_id>
work/envs/train312/bin/python -I pipeline/diagnose_ablation.py --run <hash_id>
work/envs/train312/bin/python -I pipeline/diagnose_features.py
```

## Catatan data

- 12 run: 9 berisi gangguan dan 3 normal. 27 service.
- Trace hanya ada untuk 9 dari 27 service, log untuk sekitar 13 service.
- Waktu di `spans.json` dan `logs.json` bergeser 8 jam dari metrics, dan span muncul sekitar 4 kali (duplikat). Keduanya dikoreksi di `pipeline/common.py` dan `build_traces.py`.

## Catatan penting soal evaluasi

Pembagian data acak di kode rilis EADRO bocor secara waktu: jendela test punya tetangga di train yang berbagi 9 dari 10 detiknya. Rumus HR@k versi kode asli juga dibagi dengan jumlah jendela normal yang benar, sehingga angkanya turun saat alarm palsu berkurang. Karena itu laporan memakai metrik versi baku, ditandai `(std)`, dan skema `within_event` atau `leave_event_out` sebagai ukuran yang adil. Rinciannya ada di `Report/Laporan_Tingkat_A_Protokol_Asli.md`.

## Referensi

Eadro: An End-to-End Troubleshooting Framework for Microservices on Multi-source Data. PDF paper ada di root repositori.
