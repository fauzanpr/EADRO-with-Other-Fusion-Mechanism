# Ringkasan komprehensif: reproduksi EADRO pada dataset Train Ticket

Dokumen ini merangkum **seluruh pekerjaan** dari awal sampai kondisi terakhir: tujuan, data, masalah yang ditemukan, apa yang dibangun, bagaimana hasilnya dibuktikan benar, hasil eksperimen, keterbatasan, dan langkah berikutnya.

Dokumen ini disusun dari: `Penjelasan_Pekerjaan_EADRO.md` (penjelasan teknis, 441 baris), isi file kode dan hasil di folder proyek yang saya periksa ulang (10 November 2026), dan catatan kerja sesi-sesi sebelumnya. Bagian mana yang berasal dari catatan, bukan dari pemeriksaan ulang, saya tandai.

Dua dokumen lain yang lebih ringan: `Ringkasan_Mudah_Reproduksi_EADRO.md` (versi paling sederhana) dan `work/preprocess/parsed_data/A1/Format_Data_Ekspektasi_EADRO.md` (khusus format data).

## Daftar isi

1. [Tujuan proyek](#1-tujuan-proyek)
2. [Cara kerja EADRO](#2-cara-kerja-eadro)
3. [Data yang kita punya](#3-data-yang-kita-punya)
4. [Kenapa EADRO tidak bisa langsung dijalankan](#4-kenapa-eadro-tidak-bisa-langsung-dijalankan)
5. [Format data yang diminta kode](#5-format-data-yang-diminta-kode)
6. [Pipeline data yang kita bangun](#6-pipeline-data-yang-kita-bangun)
7. [Pembagian Train / Val / Test](#7-pembagian-train--val--test)
8. [Perubahan pada kode EADRO](#8-perubahan-pada-kode-eadro)
9. [Cara membaca metrik](#9-cara-membaca-metrik)
10. [Hasil baseline](#10-hasil-baseline)
11. [Diagnosis: kenapa belum sebagus paper](#11-diagnosis-kenapa-belum-sebagus-paper)
12. [Lima varian fusion](#12-lima-varian-fusion)
13. [Daftar deviasi dari paper](#13-daftar-deviasi-dari-paper)
14. [Keterbatasan dan ancaman validitas](#14-keterbatasan-dan-ancaman-validitas)
15. [Status sekarang dan langkah berikutnya](#15-status-sekarang-dan-langkah-berikutnya)
16. [Cara menjalankan](#16-cara-menjalankan)
17. [Peta file](#17-peta-file)
18. [Glosarium](#18-glosarium)

---

## 1. Tujuan proyek

Ini tugas besar mata kuliah ML multimodal. Rencananya dua tahap:

1. **Mereplikasi** EADRO (*An End-to-End Troubleshooting Framework for Microservices on Multi-source Data*, ICSE 2023) pada dataset **Train Ticket (TT)**.
2. **Mengubah dan membandingkan mekanisme fusion**, yaitu cara model menggabungkan tiga jenis data. Perbandingan dilakukan dari sisi efektivitas (F1, HR@k, NDCG) dan efisiensi (jumlah parameter, waktu, memori).

**Kontribusi yang diklaim:** paper EADRO tidak pernah membandingkan cara fusion lain. Fusion asli mereka hanya `concat → FC → GLU`. Itulah celah penelitiannya.

**Cakupan** (dikonfirmasi 27 Oktober): hanya TT. Social Network (SN) di luar cakupan.

---

## 2. Cara kerja EADRO

### Masalah yang diselesaikan
Aplikasi TT terdiri dari **27 service** yang saling memanggil. Saat aplikasi bermasalah, EADRO menjawab dua pertanyaan untuk tiap jendela waktu 10 detik:

1. **Deteksi:** ada gangguan atau tidak?
2. **Lokalisasi:** kalau ada, service mana yang menjadi biang (*root cause*)?

### Tiga sumber data (modalitas)

| Modalitas | Perumpamaan | Isi | Bentuk per jendela |
|---|---|---|---|
| **Metrics** | Suhu dan tensi | 7 angka tiap detik per service: `cpu_usage_system/total/user`, `memory_usage`, `memory_working_set`, `rx_bytes`, `tx_bytes` | (27, 10, 7) |
| **Traces** | Rekam jejak perjalanan | Latensi panggilan antar service | (27, 10, 1) |
| **Logs** | Buku harian | Pesan teks tiap service, diubah jadi fitur angka | (27, 60) |

### Alurnya
1. Tiap modalitas dibaca **encoder** sendiri dan diringkas jadi vektor per service.
2. Tiga vektor itu **digabung (fusion)** menjadi satu vektor 64 angka per service. Di EADRO asli: tempel (`concat`), satu lapisan linear, lalu gerbang GLU.
3. Hasil fusion dipadukan dengan **graf hubungan antar service** memakai GATv2.
4. Keluar dua jawaban: **detektor** (ada gangguan?) dan **lokalizer** (service mana?).

Fusion adalah titik tempat kita nanti mengganti dan membandingkan.

---

## 3. Data yang kita punya

Sumber: `TT Dataset.zip` (sekitar 49 MB, dari Zenodo), berisi data **mentah** saja.

| Hal | Nilai |
|---|---|
| Run dengan fault | **9** (bukan 11 seperti sempat disangka) |
| Run tanpa fault | **3** |
| Total run | **12** |
| Durasi run berfault | ±6.461 detik, masing-masing berisi 9 kejadian fault |
| Durasi run tanpa fault | ±8.107 detik, total ±6,75 jam (mirip "7 jam normal" di paper) |
| Kejadian fault | **81** (27 service × 3 jenis). Paper menulis 162, jadi data kita separuhnya |
| Jenis fault | `cpu_load`, `network_delay`, `network_loss` |
| Durasi tiap fault | 601 detik |
| Celah antar fault | ±100 detik |
| Jendela (T = 10, geser 1 detik) | **82.350**, dengan 59,9% bergangguan |
| File metrics | 27 CSV per run, satu baris per detik, 7 kolom. Bersih: tanpa celah, duplikat, atau NaN |

**Hal yang wajib dipahami:** 82 ribu jendela bukan 82 ribu contoh independen. Jendela bertetangga berbagi 9 dari 10 detik. Kejadian fault yang benar-benar berbeda hanya **81**. Inilah alasan cara membagi data sangat menentukan (Bagian 7).

### Temuan tentang kondisi data
- **Waktu bergeser.** Jam pada `spans.json` dan log berselisih **+8 jam** dari jam label dan metrics. Terbukti pada 12 run: hanya dengan menggeser 8 jam, span jatuh di dalam rentang run.
- **Duplikat.** `spans.json` berisi span yang sama sekitar 4 kali, dan memuat span jauh di luar rentang run.
- **Trace jarang.** Hanya **9 dari 27 service** yang punya trace (basic, contacts, order-other, order, route, security, station, ticketinfo, verification-code). Pada 9 service itu pun hanya ±15% jendela berisi minimal satu span. Itu sifat beban kerja yang direkam, bukan kesalahan olah data.
- **Log terbatas.** Hanya sekitar **13 dari 27 service** punya log (13–15 per run). Sekitar 40% baris log adalah satu pola saja: "Span reported" dari Jaeger, bukan log aplikasi.
- **Trace memang bermakna.** Latensi pada service biang saat `network_delay` naik ×1,7 sampai ×4,4 (median ×3.000 pada catatan pengukuran ulang), saat `network_loss` naik ratusan kali, dan saat `cpu_load` tidak naik. Ini sesuai klaim paper, jadi pengaitan trace kita masuk akal.
- **Hanya 27 dari 81 fault** yang biangnya punya trace.

---

## 4. Kenapa EADRO tidak bisa langsung dijalankan

Saya membaca seluruh repo `Eadro/` lebih dulu (tanpa menjalankannya). Kesimpulannya: **bukan clone-and-run**. Ini pekerjaan membangun ulang jalur data dan memperbaiki model.

### 4.1 Format data tidak cocok
Kode meminta data olahan di `parsed_data/<nama>/` (records, traces, logs, templates, metrics). Dataset kita berupa data mentah. **Skrip pengolah mentah→olahan tidak ada** di repo maupun di Zenodo. Detail format di Bagian 5.

### 4.2 Bug pada kode
Ketujuh masalah di bawah ini tercatat saat audit kode. Saya verifikasi sebagian lewat `git diff` (enam file kode berubah, 192 baris ditambah, 54 dihapus).

| # | Masalah | Status |
|---|---|---|
| 1 | `main.py`: `chunkDataset` kekurangan argumen `edges` (padahal ada di `metadata.json`) | Diperbaiki |
| 2 | `model.py`: `trace_dropout` dan `metric_dropout` dipakai tapi tidak didefinisikan; `ConvNet` tidak menerima `dropout` | Diperbaiki |
| 3 | `model.py`: nama atribut tidak konsisten (`locator`, `detector`, `decoder_criterion` vs `localizer`, `detecter`, `detecter_criterion`) | Diperbaiki |
| 4 | `base.py`: memakai `np` tanpa `import numpy` (crash di epoch 9) | Diperbaiki |
| 5 | Tensor trace berdimensi akhir 2 (hanya indeks 0 terisi), padahal `ConvNet(1, …)` dan paper menyebut deret latensi *univariate* | Diperbaiki di sisi data: `deal_traces` kini 1 kanal |
| 6 | `single_process.py`: horizon Hawkes `end_time=e+1` (cap waktu absolut, miliaran) alih-alih panjang jendela. **Akibatnya semua fitur log konstan 6,06e-10, jadi log tidak membawa informasi apa pun** | Diperbaiki menjadi `e+1-s` |
| 7 | `align.py`: pada `split_chunks`, variabel `chunks` tidak terdefinisi bila `chunks.pkl` sudah ada | **Tidak diperbaiki**: kita tidak memakai jalur ini, karena chunk dirakit skrip sendiri |

### 4.3 Masalah desain pada kode asli
- **Pembagian acak yang bocor.** Chunk dengan stride 1 dikocok acak (`np.random.shuffle`, tanpa seed; default `test_ratio` di `split_chunks` 0,2, sedangkan catatan audit menyebut 0,3 di pemanggilnya). Jendela kembar masuk ke train dan test sekaligus.
- **Epoch terbaik dipilih memakai Test.** Itu seperti memilih jawaban sambil melihat kunci.
- **Benchmark dipilih dari huruf pertama nama dataset** (`align.py:76`): diawali "A" berarti TrainTicket (27 node), selain itu SocialNetwork (12 node). Karena itu dataset kita diberi nama `A1`.
- **Crash bila `--epoches` kurang dari 10**, karena evaluasi tidak pernah berjalan.
- **Memori boros.** Satu objek graf per contoh membutuhkan sekitar 8 GB untuk 80 ribu contoh.
- **Pin versi lama.** Repo meminta torch 1.12.1 dan dgl 0.9.1 (Python lama). Mesin kita hanya punya Python 3.12.3, tanpa GPU.

### 4.4 Fork `FeiGSSS/Eadro` tidak dipakai
Keputusan kamu. Alasannya:
- **0 dari 83.567 baris log** jatuh di jendela records (jam log tidak digeser), jadi modalitas log kosong.
- Kolom `events` ≠ `event`, dan bug Hawkes tidak diperbaiki.
- Beberapa bug saling menutupi sehingga tidak terlihat.
- Pembagian acak yang bocor, dan hanya 9 run.

### 4.5 Konsekuensi
Angka paper (F1 ≈ 0,988, HR@1 ≈ 0,982) **tidak boleh dijadikan target persis**. Semua deviasi dicatat (Bagian 13).

---

## 5. Format data yang diminta kode

Empat jenis file, per run `idx`, di `parsed_data/A1/`:

### `records{idx}.json`
```json
{ "start": 1650172861, "end": 1650179321,
  "faults": [ {"s": 1650172864, "e": 1650173464,
               "service": "ts-food-service", "type": "cpu_load"}, ... ] }
```
`get_basic` memotong run menjadi jendela `(s, s+9)` untuk setiap detik `s`. Jendela diberi label nomor node biang bila beririsan dengan fault (`overlap >= threshold`), selain itu `-1`.

### `metrics{idx}/<service>.csv`
27 file, satu baris per detik, tepat 7 kolom. `deal_metrics` melakukan z-score per kolom **atas seluruh run**, lalu mengambil baris `s..e`, dengan `assert` bahwa hasilnya persis 10 baris. Hasil: `(N, 27, 10, 7)`.

### `traces{idx}.json`
```json
{ "1650172861": {"1-26": [3.785], "20-2": [17.24, 4.921], ...}, "1650172921": {...} }
```
Kunci: detik → `"src-dst"` (nomor node) → daftar latensi (ms). `deal_traces` merata-ratakan per node tujuan per detik (slot 1 detik, hardcode), lalu z-score per node. Slot kosong bernilai 0. Hasil: `(N, 27, 10, 1)`.

### `logs{idx}.csv` + `templates.json`
```
timestamp,service,event
1650172921,ts-assurance-service,[Assurances Service][Get Assurance Type]
```
`event` adalah **template** hasil parsing; `templates.json` memuat daftar template (59 pada data kita). Id event = indeks + 1, dan 0 berarti "Unseen". `deal_logs` memasukkan waktu kemunculan per template ke model Hawkes (`HawkesADM4`) dan mengambil *baseline*-nya. Hasil: `(N, 27, 60)`.

### Satu chunk
`{traces, metrics, logs, culprit}` per jendela. Itulah yang masuk ke model.

---

## 6. Pipeline data yang kita bangun

Dibangun bertahap, satu sumber data per tahap, dan **setiap tahap diverifikasi dengan fungsi asli EADRO**.

### 6.1 Records dan metrics
- Skrip: `pipeline/common.py`, `build_records_metrics.py`, `verify_with_eadro.py`.
- Metrics disalin apa adanya (kolom sudah cocok dengan 7 `info.metric_names`).
- Konvensi label yang saya pilih (bisa diubah):
  - fault `s = floor(start)`, `e = ceil(start + duration) − 1`;
  - ambang label = 1 detik (default repo; notebook EDA kamu memakai ≥50%);
  - T = 10.
- Verifikasi (`get_basic` + `deal_metrics` asli): **58.059 jendela** untuk 9 run berfault (85,0% bergangguan), tanpa `assert` gagal, tiap service punya 1.823–1.830 jendela dengan dirinya sebagai biang.
- 3 run tanpa fault ditambahkan sebagai indeks 9–11, sehingga total 12 run dan **82.350 jendela** (59,9% bergangguan).

### 6.2 Traces
- Skrip: `build_traces.py` → `traces{0..11}.json`.
- Aturan pengaitan: *client span* (`span.kind=client`); callee = host dari `http.url`; caller = `process.serviceName`; waktu = detik mulai span − 8 jam; satuan ms; dedup `(traceID, spanID)`; filter ke jendela run.
- Verifikasi: memanggil `deal_traces` asli dan mencocokkan jumlah slot berisi dengan hitungan independen. Lolos untuk semua node.
- Pengaitan ini mengikuti paper ("latensi pemanggilan untuk tiap callee").
- **Opsi ablasi yang belum dibuat:** cadangan *server span* menambah 4 service (assurance, auth, preserve, travel), sehingga 13 dari 27 punya trace.

### 6.3 Logs
- Skrip: `build_logs.py` → `logs{0..11}.csv`, `templates.json`.
- **Drain** (`drain3==0.9.11`, `sim_th` 0,4, `depth` 4, dua tahap, penutup untuk JWT/UUID/HEX/NUM): **59 template** dari **124.571 baris**, 0 Unseen.
- **Hawkes** lewat `tick` (hanya tersedia untuk Python ≤3.9). Karena itu dibuat lingkungan terpisah `work/envs/preproc38` (Python 3.8 via `uv`, numpy 1.21.5, pandas 1.4.2, tick 0.7.0.1; skrip `setup_preproc_env.sh`).
- Biaya: ±70 ms per jendela, ±1 jam CPU untuk semua run di 8 core. Hasil per run disimpan di cache (`build_run_caches.py` → `work/chunks/A1/<idx>/{traces,metrics,logs}.pkl`).
- Verifikasi (`verify_caches.py`): aktivitas log pada fitur cocok dengan baris log di CSV, **0 ketidakcocokan**.

**Keterbatasan fitur log (setia ke kode asli, tidak diperhalus):** setelah bug horizon diperbaiki, nilai Hawkes *jenuh* di sekitar 0,1. Pola yang tidak muncul dan pola yang muncul 1–10 kali hampir tidak dibedakan (median 0,1000 vs 0,1035; korelasi Spearman 0,35). Praktisnya fitur log kira-kira berarti "service ini punya log di jendela ini atau tidak".

### 6.4 Rakit dan bagi
`build_chunks_split.py` merakit chunk dan membaginya (Bagian 7). Chunk disimpan sebagai float32, ±1,2 GB per skema.

### 6.5 Catatan normalisasi
Z-score dihitung **per run** (kode asli). Run berfault punya nilai ekstrem akibat fault jaringan (|z| maksimum 32–80), jadi skala run tanpa fault berbeda dengan run berfault. Keputusan apakah ini diubah **masih terbuka** (Bagian 15).

---

## 7. Pembagian Train / Val / Test

### Masalah yang dipecahkan
Jendela yang digeser 1 detik hampir kembar. Pembagian acak membuat Train dan Test saling mengintip (**kebocoran**), sehingga nilai terlihat bagus padahal menipu.

### Caranya
Pembagian dilakukan **per detik berdasarkan waktu**. Sebuah jendela dipakai hanya bila **semua 10 detiknya** berlabel sama; jendela yang melintasi batas dibuang (*purge*). Terbukti dengan program pemeriksa terpisah: **0 detik dipakai bersama** antar split pada kedua skema.

### Dua skema

| | `within_event` | `leave_event_out` |
|---|---|---|
| Ide | Tiap wilayah fault dipotong menurut waktu: 50% awal Train, 10% Val, 40% akhir Test | Untuk tiap service, **satu jenis fault** disisihkan seluruhnya untuk Test (27 kejadian test, 9 per jenis), ditambah run tanpa fault terakhir |
| Pertanyaan | Bisakah mengenali fault yang pola serupanya sudah pernah dilihat? | Bisakah menggeneralisasi ke jenis fault yang belum pernah dilihat untuk service itu? |
| Train | 40.510 (24.823 bergangguan, 15.687 normal) | 46.160 (30.029 bergangguan, 16.131 normal) |
| Val | 7.490 | 7.695 |
| Test | 32.190 | 27.352 |
| Dibuang (*purge*) | 2.160 | 1.143 |
| Total dipakai | 80.190 | 81.207 |

Jumlah di atas saya cek dari `split_summary.json`: train + val + test + dibuang = 82.350 pada kedua skema. Semua 27 service punya contoh di ketiga split.

### Kelemahan `within_event` (ditemukan setelah training pertama)
Val-nya **tidak memuat jendela normal dari run berfault**. Hanya run tanpa fault yang jadi normal di Val. Akibatnya Val tidak mewakili Test, dan nilai Val tampak bagus sementara Test jelek. `leave_event_out` tidak memiliki kelemahan ini, karena Val-nya memuat normal pasca-fault (5.307 jendela normal). Karena itu `leave_event_out` dipilih sebagai skema utama untuk perbandingan fusion.

---

## 8. Perubahan pada kode EADRO

Repo `Eadro/` hanya punya 1 commit asli (7 Februari 2023). Perubahan kita belum di-commit (`git status` menunjukkan 6 file `M`).

| File | Perubahan | Alasan |
|---|---|---|
| `main.py` | Teruskan `edges`; muat Val; dataset memakai satu graf bersama, graf per batch dirakit di `make_collate`; baris log efisiensi | Bug, memori |
| `base.py` | `import numpy`; pilih epoch via Val; Test hanya dihitung pada epoch terpilih; cadangan evaluasi bila epoch < 10; metrik `(std)`; `--select_metric`, `--eval_every` | Bug, kebocoran, pelaporan |
| `utils.py` | `load_chunks` mengembalikan train/val/test | Mendukung Val |
| `model.py` | Perbaiki dropout dan nama atribut; tambah `--fusion` dengan 5 pilihan | Bug, fusion |
| `preprocess/single_process.py` | Trace 1 kanal; horizon Hawkes `e+1-s` | Bug, sesuai paper |
| `preprocess/align.py` | Hanya komentar ukuran tensor | Dokumentasi |

### Bukti bahwa perubahan memori tidak mengubah hasil
Perubahan "satu graf bersama" membuat peak RSS turun dari sekitar 8 GB menjadi **2,9 GB**. Hasilnya diverifikasi **identik** dengan cara lama (struktur graf, `ndata`, label) pada 6 chunk.

### Smoke test
Model dijalankan pada data sintetis dengan pola yang sengaja ditanam per service (`smoke_test/`). Hasil deterministik. Percobaan pertama saya salah rancang (pola sama untuk semua service, sehingga HR@1 mendekati tebakan acak). Itu kesalahan data uji, bukan bug model, dan sudah diperbaiki.

### Lingkungan Python
| Lingkungan | Isi | Kegunaan |
|---|---|---|
| `work/envs/preproc38` | Python 3.8, numpy 1.21.5, pandas 1.4.2, tick 0.7.0.1 | Pengolahan data (Hawkes) |
| `work/envs/train312` | Python 3.12, torch 2.2.1 (CPU), dgl 2.1.0, numpy<2, scikit-learn 1.5.2, ipykernel, matplotlib | Training dan membaca hasil |

Ini bukan pin repo asli (torch 1.12.1 dan dgl 0.9.1). DGL 2.1 hanya mendukung torch sampai 2.2.1. Uji 1 epoch pada env lama dan env baru memberi hasil identik.

---

## 9. Cara membaca metrik

Kode asli menghitung metrik dengan cara yang membuat angkanya sulit dibaca:

1. **"F1" bukan F1 baku kelas gangguan.** Jendela *normal* yang ditebak normal ikut dihitung sebagai *true positive*. F1, Recall, Precision jadi mencampur dua kelas.
2. **Penyebut HR@k = TP + FN**, yang ikut memuat jendela normal yang benar. Akibatnya HR@k asli *lebih rendah* dari "persentase jendela bergangguan yang biangnya tertebak benar". Pada Test `within_event`, batas atasnya sekitar 0,74.

**Penanganan (disetujui):** angka asli **tetap dicetak** (agar sebanding dengan paper). Di sampingnya ditambahkan versi baku berakhiran `(std)`:

| Kunci | Arti |
|---|---|
| `F1`, `Rec`, `Pre`, `HR@k`, `ndcg@k` | Versi kode asli |
| `F1(std)`, `Rec(std)`, `Pre(std)` | Deteksi untuk kelas gangguan saja |
| `HR@k(std)`, `ndcg@k(std)` | Dibagi jumlah jendela bergangguan; gangguan yang terlewat dihitung gagal |

Diverifikasi dengan hitungan independen dari prediksi mentah (cocok sampai 1e-9). Relasinya: `HR@k(asli) × (TP+FN) = HR@k(std) × jumlah_jendela_bergangguan`.

**Kriteria pemilihan epoch.** Default sekarang `--select_metric combo` = rata-rata `F1(std)` dan `HR@1(std)` di Val. Alasannya: HR@1 versi asli justru *turun* saat model mengurangi alarm palsu (di `leave_event_out`, dari epoch 9 ke 29: presisi Val naik 0,44→0,48 dan HR@1(std) Val naik 0,87→0,90, tetapi HR@1 asli turun 0,435→0,409, sehingga epoch 9 yang dipertahankan).

**Tebakan acak** untuk HR@1 adalah 1/27 ≈ 0,037.

---

## 10. Hasil baseline

Dibaca dari `work/result/ringkasan_hasil.csv` dan `experiments.txt` (diperiksa ulang). Semua run memakai fusion asli `concat_glu`, seed 42, dan kriteria pemilihan lama (HR@1 asli di Val).

| | Uji 1 epoch | Baseline `within_event` | Baseline `leave_event_out` |
|---|---|---|---|
| Run | `49129d05` | `9df622b8` | `d574273b` |
| Epoch diminta / terpilih | 1 / 1 | 50 / **9** | 30 / **9** |
| Waktu latih | 1,3 menit | 53,4 menit | 34,7 menit |
| Detik per epoch | 77,7 | 64,1 | 69,3 |
| Val HR@1(std) | 0,413 | 0,913 | 0,871 |
| **Test HR@1(std)** | 0,355 | **0,808** | **0,539** |
| Test HR@3(std) | 0,597 | 0,875 | 0,666 |
| Test HR@5(std) | 0,676 | 0,889 | 0,731 |
| Test NDCG@3(std) | 0,494 | 0,849 | 0,613 |
| Test NDCG@5(std) | 0,527 | 0,855 | 0,640 |
| **Test F1(std)** | 0,755 | **0,765** | **0,780** |
| Test F1 (asli) | 0,815 | 0,816 | 0,825 |
| Test HR@1 (asli) | 0,259 | 0,607 | 0,418 |

### Perbandingan dengan paper
Angka TT di paper menurut catatan sesi sebelumnya (**cek ulang ke PDF sebelum dikutip di laporan**): F1 ≈ 0,989 (Pre 0,984, Rec 0,995), HR@1/3/5 ≈ 0,990/0,992/0,993. Angka 0,988 dan 0,982 yang sering terbaca adalah rata-rata TT dan SN.

| | Paper (TT) | Kita (`leave_event_out`) |
|---|---|---|
| F1 | ≈ 0,989 | 0,78 (std) / 0,83 (asli) |
| HR@1 | ≈ 0,990 | 0,54 (std) / 0,42 (asli) |

**Jangan dibandingkan langsung.** Data kita separuh dari paper, pembagian kita jauh lebih ketat (paper membagi 60/40 per periode), epoch dipilih dengan Val, dan definisi metrik berbeda.

### Hal yang terbaca dari hasil
- Lokalisasi jelas belajar: 0,54–0,81 vs acak 0,037.
- `within_event` jauh lebih mudah daripada `leave_event_out` (0,81 vs 0,54). Itu wajar: pada skema kedua, jenis fault tertentu untuk satu service tidak pernah dilihat saat belajar.
- Epoch terpilih selalu **epoch 9**, yaitu evaluasi pertama. Setelah itu Val datar sementara *training loss* terus turun (0,12 → 0,03): model mulai menghafal. 50 epoch tidak diperlukan; 15–20 cukup.
- Pada run 50 epoch, laptop sempat tidur sekitar 3,3 jam di epoch 39. Tidak memengaruhi hasil.

---

## 11. Diagnosis: kenapa belum sebagus paper

Skrip: `pipeline/diagnose_alarm.py`, `diagnose_features.py`, `diagnose_ablation.py`. Keluaran: `work/result/9df622b8/diagnosis_*.txt/csv`.

### 11.1 Gejala
Presisi deteksi **turun dari 0,94 (Val) ke 0,66 (Test)** pada `within_event`. Alarm palsu pada jendela normal: Train 19%, Val 12%, **Test 58%**. Pada `leave_event_out`, sekitar 55–56% jendela normal di Val dan Test ditandai bergangguan. Jadi masalah ini **bukan sekadar akibat cara membagi data**.

### 11.2 Dua sumber alarm palsu

**A. Jendela normal di antara dua gangguan (run berfault).**
Alarm palsu ≈ 80% di Train (82%, *in-sample*) maupun Test (80%), pada semua jarak dari gangguan. Jadi model tidak pernah belajar membedakan "celah" dari "gangguan", bahkan pada data yang dipelajarinya. Sebab belum diketahui.

**B. Jendela normal di run tanpa fault.**
Alarm palsu naik makin jauh dari blok Train: 0,5% (Train), 12% (Val), 48% (Test). Per run pada Test: run 9 = 6%, run 10 = 55%, run 11 = 82%. Alarm muncul **mendadak** sekitar detik ke-4.000–4.800 pada run 10 dan 11, bukan perlahan. Pemicunya belum ditemukan.

### 11.3 Yang terukur tentang fitur
1. **`cpu_load`:** metrics service biang melonjak sekitar 30σ-robust persis selama jendela berlabel, lalu kembali normal segera. Jadi dugaan "label meleset" atau "efek sisa CPU" **tidak terbukti** (sisa `memory_working_set` mengecil dari 5 ke 0,5 dalam 120 detik).
2. **`network_delay` / `network_loss`:** 7 metrics service biang **hampir tidak bereaksi** (≤0,15). Efeknya hanya mungkin muncul di trace atau di service lain.
3. **Jendela normal tidak homogen.** Classifier non-linear pada ringkasan metrics membedakan normal di run tanpa fault dari normal di run berfault dengan **AUC 0,98** (CPU saja 0,996; memory 0,43; jaringan 0,75; log + trace 0,60). Antara jendela celah dan jendela bergangguan, AUC hanya 0,73. Catatan: uji linear hanya 0,60, jadi bukti ini tidak sepenuhnya konklusif.
4. **Oklusi pada model yang sudah dilatih** (menolkan input; petunjuk arah, bukan bukti pasti):
   - **Log dinolkan → tidak ada perubahan.** Log tidak berperan.
   - **Memory dinolkan → semua alarm hilang** (recall 0,2%).
   - **CPU dinolkan →** recall turun 90% → 60%, alarm palsu turun sekitar sepertiga.
   - Untuk fault jaringan, memory milik **service biang sendiri tidak berpengaruh**, tetapi memory **service lain** menentukan (recall 94% → 13%).
   - **Trace dinolkan → semua jadi alarm** (di luar distribusi latih).
5. **Memory tidak berubah serentak di batas fault** (1–3 dari 27 service per 11 detik, sama dengan acak). Jadi bukan "kenaikan memori serentak" yang memicu alarm.

### 11.4 Lemah per jenis fault
Test `within_event`: `network_loss` terlemah (terdeteksi 77%, top-1 benar 71%), dibanding `cpu_load` (99,5% dan 92%) dan `network_delay` (94% dan 96%).

### 11.5 Tafsiran (**belum terbukti**)
Deteksi tampaknya banyak bersandar pada **ciri tingkat-run** (skala z-score per run, dan kanal memory service lain), bukan pada efek gangguan di service biang. Dugaan "perbedaan skala antar-run" dicek secara kasar (|z| rata-rata awal 0,411 vs akhir 0,406 vs normal berfault 0,405) dan tidak didukung, tetapi belum dikecualikan untuk per kanal/service.

### 11.6 Dampak untuk proyek
- Model baseline secara praktis **bersandar pada metrics**; log tidak berperan, trace hanya berperan sebagai masukan.
- Bila varian fusion dibandingkan di atas pengaturan ini, selisihnya bisa lebih mencerminkan cara memproses ciri tingkat-run daripada kualitas penggabungan beberapa sumber.
- Lokalisasi (`HR@k(std)`) lebih bisa dipercaya daripada deteksi. Angka F1/Precision deteksi mutlak belum boleh dipakai untuk klaim "model bagus atau jelek".

---

## 12. Lima varian fusion

Tiga encoder menghasilkan trace (64), metrics (64), dan log (16) per service. Fusion menggabungkannya menjadi **satu vektor 64 angka per service**, lalu masuk ke graf. Bagian lain model tidak diubah, sehingga hanya cara penggabungan yang berbeda. Dipilih lewat `--fusion`.

| `--fusion` | Cara kerja | Parameter fusion |
|---|---|---|
| `concat_glu` | **Asli EADRO**: tempel, satu linear, gerbang GLU | 18.560 |
| `concat_fc` | Tempel, linear, ReLU (tanpa gerbang GLU) | 9.280 |
| `sum` | Proyeksi tiap sumber ke 64 angka, lalu dijumlahkan; tanpa interaksi | 9.408 |
| `attn` | Proyeksi lalu bobot softmax per sumber per service (bobot bisa dianalisis) | 9.473 |
| `lmf` | *Low-rank multimodal fusion* (Liu dkk., 2018): perkalian antar sumber | 37.696 |

Angka parameter bisa diperiksa: `concat_glu` = 144 × 128 + 128 = 18.560, `concat_fc` = 144 × 64 + 64 = 9.280.

**Diuji:** semua varian jalan di smoke test, dan empat varian baru jalan 2 epoch pada data asli `leave_event_out` tanpa NaN (±58–70 detik per epoch, RAM puncak 2,8 GB, inferensi ≈ 0,26–0,29 ms per jendela). Hasil 2 epoch **tidak bermakna** untuk perbandingan.

**Efisiensi dicatat otomatis** di tiap run: parameter total dan fusion, ms per jendela, RAM puncak, detik per epoch.

**Ketidakcocokan dengan laporan:** slide 11 di `Report/Progress 3.pptx` menulis 4 kandidat fusion (F1–F4, termasuk Cross-Attention), sedangkan kode punya 5 dan Cross-Attention belum ada. Perlu diputuskan: tambah Cross-Attention ke kode atau ubah slide.

---

## 13. Daftar deviasi dari paper

Untuk bagian "metode" laporan:

1. Kode rilis tidak bisa dijalankan apa adanya, dan jalur mentah→olahan tidak tersedia, jadi ini **re-implementasi** dengan perbaikan.
2. Data kita **81 kejadian fault** (paper: 162).
3. Pembagian data **per waktu dengan *purge*** (paper: 60/40 per periode; kode: acak dan bocor).
4. Epoch dipilih memakai **Val**, bukan Test.
5. Bug horizon Hawkes diperbaiki; jalur trace dibuat 1 kanal.
6. Metrik dilaporkan dalam dua versi (asli dan `(std)`).
7. Trace hanya mencakup 9 dari 27 service, log 13 dari 27 (sifat data).
8. Fitur log (Hawkes) jenuh dan hampir tidak informatif.
9. Normalisasi z-score **per run** (setia kode asli).
10. Konvensi label fault dan ambang 1 detik adalah pilihan kita.
11. Lingkungan: torch 2.2.1 dan dgl 2.1.0 pada CPU (bukan pin repo).
12. Pemilihan epoch dengan kriteria `combo` (setelah baseline).

---

## 14. Keterbatasan dan ancaman validitas

1. **Model bersandar pada metrics** dan log tidak berperan (Bagian 11). Perbandingan fusion bisa tidak mencerminkan kualitas penggabungan multi-sumber.
2. **Alarm palsu ±55%** pada jendela normal masih ada, sehingga F1 deteksi mencerminkan keterbatasan ini.
3. Dugaan ketergantungan pada ciri tingkat-run **belum terbukti**. Percobaan kontrol dengan normalisasi lain adalah pekerjaan lanjutan.
4. Hanya **TT**, hanya **3 seed** yang direncanakan, hanya **9 run berfault**.
5. Seed tunggal pada baseline: selisih antar varian yang lebih kecil dari simpangan baku antar seed **tidak boleh dikatakan sebagai perbedaan**.
6. Kode asli evaluasi pertama di epoch 9, jadi sebelum perubahan `--eval_every 5` kita tidak tahu apakah epoch yang lebih awal lebih baik.
7. Hasil baseline di atas memakai kriteria pemilihan epoch lama (HR@1 asli); grid fusion akan memakai `combo`.
8. Beberapa angka diagnosis berasal dari Recall/Precision yang dibulatkan, jadi berupa perkiraan.

---

## 15. Status sekarang dan langkah berikutnya

### Sudah selesai
- Audit kode, perbaikan bug, smoke test.
- Pipeline data lengkap (records, metrics, traces, logs), cache, dan dua skema pembagian.
- Perubahan training (Val, hemat memori, metrik `(std)`, `combo`, `eval_every`, log efisiensi).
- Dua baseline penuh (`within_event`, `leave_event_out`) dan diagnosis.
- Kode lima varian fusion, `run_grid.sh`, pembaca hasil (`baca_hasil.py`, `Hasil_Training.ipynb`).
- Laporan Progress 3 (30 slide: EDA di slide 17–21, baseline di slide 23–29) dan panduan belajar `Report/Penjelasan_EDA_dan_Baseline.md`.

### Belum dikerjakan (diperiksa: `work/result/` tidak memuat `grid_selesai.txt`, dan tidak ada run setelah 27 Oktober)
1. **Grid fusion belum dijalankan.** Rencana: `leave_event_out`, 5 fusion × seed 42/7/123, 15 epoch, ±20 menit per run, ±5 jam CPU total.
2. **Keputusan tentang alarm palsu** (kamu yang memutuskan). Pilihan:
   - (1) normalisasi yang tidak bergantung pada run (statistik dari data normal saja), latih ulang 15–20 epoch (±20 menit), lalu uji ulang AUC normal-tanpa-fault vs normal-berfault. **Ini rekomendasi saya.**
   - (2) latih tanpa kanal memory atau CPU untuk melihat perannya.
   - (3) catat sebagai keterbatasan dan lanjut ke fusion ("jalan tengah" yang sudah kita sepakati sebelumnya).
3. Ketidakcocokan slide 11 dengan kode (Bagian 12).
4. Opsional: kolom "benchmark (TT, 27 node)" di tabel hasil (tawaran belum dijawab); fallback server span untuk trace (13/27); ablasi T dan slot trace (notebook EDA kamu memakai T = 60, slot 5 detik, label ≥50%).
5. Commit perubahan kode di `Eadro/` bila diperlukan (saat ini belum).

### Keputusan yang masih terbuka
| Keputusan | Pilihan | Catatan |
|---|---|---|
| Normalisasi | Per run (sekarang) vs statistik dari data normal | Memengaruhi alarm palsu |
| Panjang jendela dan slot trace | Setia Eadro (T = 10, slot 1 s) vs EDA kamu (60 s, 5 s) | Usul: setia dulu, ablasi belakangan |
| Ambang label | ≥1 detik (sekarang) vs ≥50% | |
| Skema utama | `leave_event_out` (usul) | `within_event` Val-nya tidak mewakili Test |
| Cross-Attention | Tambahkan atau hapus dari slide | |

---

## 16. Cara menjalankan

Semua perintah dari folder proyek. Training dijalankan olehmu sendiri (keputusanmu).

```bash
# Satu training: <skema> [seed] [epoch] [argumen main.py]
pipeline/run_train.sh within_event 42 1          # uji cepat 1 epoch (±3 menit)
pipeline/run_train.sh leave_event_out 42 15 --fusion attn

# Seluruh grid, berurutan; aman dihentikan lalu diulang (run selesai dilewati)
nohup pipeline/run_grid.sh leave_event_out 15 "42 7 123" "concat_glu concat_fc sum attn lmf" > grid_leo.out 2>&1 &

# Memantau
tail -f work/result/<hash_id>/running.log

# Tabel dan gambar (termasuk perbandingan fusion)
work/envs/train312/bin/python pipeline/baca_hasil.py
```

- Evaluasi Val dilakukan pada epoch 4, 9, 14, … (`--eval_every 5`). Baris `Test` hanya muncul bila Val membaik.
- Hasil: `work/result/<hash_id>/`, ringkasan teks `experiments.txt`, tabel `ringkasan_hasil.csv`, grafik di `gambar/`.
- Notebook `Hasil_Training.ipynb` memakai kernel `work/envs/train312/bin/python`.
- Selama training, hindari pekerjaan berat lain (8 core terpakai). Jangan ubah isi `work/chunks/` di tengah rangkaian eksperimen. Jangan menimpa folder hasil.
- Log dengan parameter identik di-*append* ke hash yang sama, sehingga parser hanya membaca percobaan terakhir.

Pembuatan ulang lingkungan: `pipeline/setup_train_env.sh` (±2 menit, butuh internet; jalur proyek berspasi) dan `pipeline/setup_preproc_env.sh`.

---

## 17. Peta file

| Lokasi | Isi |
|---|---|
| `TT Dataset/`, `TT Dataset.zip` | Data mentah asli (tidak diubah) |
| `[1][2] Eadro_…pdf` | Paper EADRO |
| `Eadro/codes/` | Kode model yang sudah diperbaiki |
| `pipeline/common.py` | Pengaturan dan fungsi bersama |
| `pipeline/build_records_metrics.py`, `build_traces.py`, `build_logs.py` | Pengolah data mentah |
| `pipeline/build_run_caches.py` | Hitung fitur per run (Hawkes) |
| `pipeline/build_chunks_split.py` | Rakit chunk dan bagi Train/Val/Test |
| `pipeline/verify_with_eadro.py`, `verify_caches.py` | Pemeriksa independen |
| `pipeline/run_train.sh`, `run_grid.sh`, `setup_*_env.sh` | Menjalankan training dan menyiapkan env |
| `pipeline/baca_hasil.py` | Tabel dan grafik hasil |
| `pipeline/diagnose_alarm.py`, `diagnose_features.py`, `diagnose_ablation.py` | Diagnosis alarm palsu |
| `smoke_test/` | Uji model dengan data buatan |
| `work/preprocess/parsed_data/A1/` | Data olahan (records, metrics, traces, logs, templates) |
| `work/chunks/A1/{within_event, leave_event_out}/` | Data siap latih + `split_summary.json` |
| `work/result/` | Hasil training, `ringkasan_hasil.csv`, `gambar/` |
| `work/envs/` | Lingkungan Python (`preproc38`, `train312`) |
| `work/raw_nofault/` | Run tanpa fault yang diekstrak |
| `Penjelasan_Pekerjaan_EADRO.md` | Penjelasan teknis lengkap |
| `Ringkasan_Mudah_Reproduksi_EADRO.md` | Ringkasan sederhana |
| `Report/` | Slide Progress 3 dan panduan belajar |
| `EDA.ipynb`, `EDA_Alur_Data_EADRO.ipynb`, `EDA_Multimodal_Sederhana.ipynb`, `Contoh_Trace_1_Request.ipynb`, `Hasil_Training.ipynb` | Notebook |

---

## 18. Glosarium

| Istilah | Arti |
|---|---|
| **Service / node** | Satu komponen aplikasi. Ada 27 di TT. |
| **Fault** | Gangguan yang sengaja disuntikkan: `cpu_load`, `network_delay`, `network_loss`. |
| **Culprit / biang** | Service tempat fault disuntikkan; jawaban benar untuk lokalisasi. `-1` bila normal. |
| **Run** | Satu sesi percobaan yang direkam utuh. |
| **Jendela / chunk** | Potongan 10 detik yang menjadi satu contoh. Digeser 1 detik, sehingga bertetangga hampir kembar. |
| **Train / Val / Test** | Belajar / memilih model / ujian akhir. |
| **Kebocoran (*leakage*)** | Ujian yang soalnya sudah pernah dilihat saat belajar. |
| **Purge** | Membuang jendela yang melintasi batas split. |
| **Epoch** | Satu putaran membaca seluruh data latih. |
| **Seed** | Angka awal pengacak; seed berbeda memberi hasil sedikit berbeda. |
| **Fusion** | Cara menggabungkan ringkasan trace, metrics, dan log. |
| **Encoder** | Bagian model yang meringkas satu modalitas. |
| **GLU** | *Gated Linear Unit*, gerbang pada fusion asli EADRO. |
| **GATv2** | Jenis jaringan graf yang memadukan hubungan antar service. |
| **Drain** | Algoritma pengelompokan baris log ke template. |
| **Hawkes** | Model titik waktu yang dipakai mengubah kemunculan template menjadi fitur angka. |
| **F1, Recall, Precision** | Ukuran kualitas deteksi. |
| **HR@k** | *Hit Rate*: seberapa sering biang asli ada di k tebakan teratas. |
| **NDCG@k** | Seperti HR@k, tetapi tebakan benar di peringkat atas bernilai lebih. |
| **`(std)`** | Versi baku metrik (kelas gangguan saja), berbeda dengan versi kode asli. |
| **AUC** | Ukuran seberapa baik sebuah pengklasifikasi memisahkan dua kelompok (0,5 = acak, 1 = sempurna). |
| **Oklusi** | Menolkan satu input pada model yang sudah dilatih untuk melihat seberapa ia bergantung padanya. |
