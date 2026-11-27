# Jurnal Eksperimen: Alur, Alasan, dan Hasil

| | |
|---|---|
| Dibuat | 26 November 2026 |
| Isi | Semua eksperimen dari awal, **urut waktu**. Tiap entri menjawab: masalah apa yang memicunya, apa yang dilakukan, hasilnya, dan apa akibatnya untuk langkah berikutnya |
| Bedanya dengan laporan lain | Laporan lain (`Perbandingan_Seluruh_Eksperimen.md`, `Laporan_Fusion_F1_vs_F2.md`, dst.) berisi tabel lengkap per eksperimen. Jurnal ini adalah **benang merahnya**: kenapa eksperimen B dibuat setelah A. Angka di sini hanya yang penting; rinciannya ada di laporan yang dirujuk |
| Metrik | Test, versi (std), pada epoch yang dipilih lewat Val, rata-rata ± sd antar seed. FPR = alarm palsu / jumlah jendela normal (turunan, lihat `pipeline/banding_fusion.py`) |
| Aturan pembaruan | Setiap eksperimen baru ditambahkan sebagai entri baru di bagian 2 dengan format di bagian 5. Rencana yang sudah dijalankan dipindah dari bagian 4 ke bagian 2 |

Nama fusion: **F1** = `concat_glu` (asli EADRO: concat → Linear → GLU), **F2** = `concat_fc` (tanpa GLU), **F3** = `gmu` (Gated Multimodal Unit), **F1w** = `concat_glu_wide` (F1 diperbesar setara F3). Skema: `within_event` (event yang sama ada di latih dan uji) dan `leave_event_out` (event uji belum pernah dilihat; skema yang lebih ketat).

---

## 1. Peta singkat

```
Tujuan: replikasi EADRO di Train Ticket, lalu bandingkan mekanisme fusion
 │
 ├─ E1  Pipeline data + baseline seed 42 ........ angka jauh di bawah paper
 ├─ E2  Baseline 3 seed ......................... sebaran seed besar, alarm palsu ±60%
 ├─ E3  Temuan trace + T = 5 .................... trace datang tiap ±60 dtk → coba T lain
 ├─ E4  Protokol asli (random_original) ......... selisih ke paper = kebocoran protokol
 ├─ E5  Efisiensi baseline F1 ................... acuan biaya
 ├─ E6  F2: apakah GLU perlu? ................... tidak (F2 ≈ F1)
 ├─ E7  Sweep T = 30…60 ......................... deteksi naik s.d. T = 50, lokalisasi tidak
 ├─ E8  Tambah seed 31, 2026 (n = 5) ............ CI n = 3 terlalu lebar
 ├─ E9  F3 (GMU) di T = 10 ...................... F3 ≥ F1, tipis
 ├─ E10 Cek epoch T = 30 ........................ 15 epoch kurang di leave_event_out → 30
 ├─ E11 Fusion di T = 30 within_event ........... ketiganya setara
 ├─ E12 Fusion di T = 30 leave_event_out ........ F3 unggul deteksi (FPR 0,24 vs 0,44)
 ├─ E13 F1w: kapasitas atau mekanisme? .......... T = 10: kapasitas; T = 30: mekanisme GMU
 └─ E14 T = 10 leave_event_out, 30 epoch ........ tidak berubah → efek GMU bergantung T, bukan epoch
      │
      └─ Berikutnya (bagian 4): fusion tambahan (sum, attn, lmf), analisis gate, T = 50
```

---

## 2. Entri eksperimen

### E1. Pipeline data dan baseline pertama (s.d. 27 Oktober)

- **Masalah.** Kode EADRO tidak bisa langsung dijalankan pada data publik Train Ticket. Format data mentah berbeda dari yang diminta kode, ada selisih jam 8 jam antara spans/logs dan label/metrics, dan spans terduplikasi ±4×.
- **Yang dilakukan.** Membangun pipeline praproses (log, metric, trace → chunk per jendela), membuat dua skema pembagian yang adil (`within_event`, `leave_event_out`), lalu melatih F1 dengan seed 42.
- **Hasil.** Model berjalan, tetapi angkanya jauh di bawah paper (paper TT: F1 0,989, HR@1 0,990).
- **Akibat.** Perlu tahu apakah angka itu kebetulan (→ E2), dan dari mana selisih ke paper (→ E4).
- **Rincian.** `Ringkasan_Komprehensif_Reproduksi_EADRO.md`, `Penjelasan_Pekerjaan_EADRO.md`.

### E2. Baseline 3 seed (10 November)

- **Masalah.** Satu run (seed 42) tidak menunjukkan apakah hasilnya kebetulan. Saran dosen: pakai 3 seed.
- **Yang dilakukan.** F1, T = 10, seed 42, 7, 123, kedua skema (6 run).
- **Hasil.** `leave_event_out`: F1 0,806 ± 0,036, HR@1 0,650 ± 0,099. Recall tinggi (0,92–0,94), tetapi ±60% jendela normal dialarm. HR@1 berkisar 0,566–0,759 hanya karena ganti seed.
- **Akibat.** (1) Kelemahan utama adalah **alarm palsu**, bukan gangguan yang terlewat. (2) Dengan 3 seed, CI 95% HR@1 selebar ±0,25, jadi perbedaan fusion yang kecil tidak akan terdeteksi (→ E8).
- **Rincian.** `Laporan_Eksperimen_Seed.md`.

### E3. Temuan data trace dan T = 5 (10 November)

- **Masalah.** Dosen menyarankan mencoba panjang jendela T yang lebih kecil dan lebih besar. Saat diperiksa, trace di data kita datang dalam **lonjakan 1 detik tiap ±60 detik**, sehingga pada T = 10 hanya ±18% jendela memuat satu pun span. Modalitas trace hampir kosong di sebagian besar jendela.
- **Yang dilakukan.** Menghitung cakupan trace per T, lalu menjalankan T = 5 (`within_event`, 3 seed).
- **Hasil.** T = 5 tidak berbeda nyata dari T = 10 (F1 −0,024, HR@1 −0,023, semua CI memuat 0). Cakupan trace kira-kira sebanding dengan T/60, jadi T besar (30–60) layak dicoba.
- **Akibat.** Sweep T ke atas (→ E7).
- **Rincian.** `Temuan_Data_dan_Sweep_T.md` bagian 2–4 dan 10.

### E4. Tingkat A: meniru protokol kode asli (16 November)

- **Masalah.** Dosen meminta angka mendekati paper. Sebelum mengubah model, perlu diketahui apakah selisih ke paper datang dari model atau dari cara evaluasi.
- **Yang dilakukan.** Skema `random_original`: jendela dibagi acak seperti di kode rilis EADRO, 50 epoch, 3 seed. Model dan data tetap sama.
- **Hasil.** F1(std) 0,964, HR@1(std) 0,963, hampir sama dengan paper. Tetapi pembagian acak **bocor waktu**: hampir tiap jendela test punya tetangga di train yang berbagi 9 dari 10 detiknya. Selain itu, rumus HR@k di kode asli cacat (ikut menghitung jendela normal).
- **Akibat.** Angka paper tidak bisa dijadikan target yang adil. Semua perbandingan selanjutnya memakai skema adil dan metrik (std).
- **Rincian.** `Laporan_Tingkat_A_Protokol_Asli.md`.

### E5. Efisiensi baseline F1 (16 November)

- **Masalah.** Perbandingan fusion juga harus dari sisi biaya, jadi perlu acuan.
- **Yang dilakukan.** Mencatat parameter, waktu inferensi, waktu per epoch, dan memori puncak di akhir tiap run (`log_efficiency()` di `Eadro/codes/main.py`).
- **Hasil.** F1 T = 10: 66.050 parameter (18.560 di fusion), ±0,27 ms per jendela, ±51–58 detik per epoch, ±2,75 GB RAM. Perangkat: laptop i7-8650U, CPU saja.
- **Rincian.** `Laporan_Efisiensi_F1.md`.

### E6. F2: apakah gate GLU diperlukan? (16 November, diperbarui 22 November)

- **Masalah.** Fusion asli EADRO memakai GLU. Paper tidak pernah menguji apakah GLU itu penting. Ini pertanyaan pertama dari studi fusion.
- **Yang dilakukan.** F2 = F1 tanpa GLU (`concat → Linear → ReLU`), T = 10, kedua skema, akhirnya 5 seed.
- **Hasil.** F2 ≈ F1. Satu-satunya selisih yang lolos adalah F1(std) `within_event` +0,043 (CI +0,005 s.d. +0,081), dan tidak berulang di skema lain.
- **Akibat.** Gate setelah pencampuran (GLU) tidak terbukti perlu. Pertanyaan berikutnya: bagaimana kalau gate diletakkan **per modalitas**, sebelum pencampuran (→ E9).
- **Rincian.** `Laporan_Fusion_F1_vs_F2.md` bagian 1–9.

### E7. Sweep T = 30, 40, 50, 60 (17–22 November)

- **Masalah.** Lanjutan E3: apakah jendela yang lebih panjang (lebih banyak trace) memperbaiki model?
- **Yang dilakukan.** F1, 3 seed, kedua skema, 15 epoch, tanpa stride.
- **Hasil.** Deteksi naik sampai T = 50 lalu mendatar (`leave_event_out` F1: 0,806 → 0,837 → 0,877 → 0,905 → 0,896 untuk T = 10/30/40/50/60). Alarm palsu turun dari 0,59 ke ±0,4. **Lokalisasi tidak membaik** (HR@1 `leave_event_out` T besar 0,52–0,58, di bawah T = 10 yang 0,650). Dengan n = 3, hampir tidak ada selisih yang signifikan. Biaya naik hampir linear terhadap T (T = 60: ±5× waktu latih, RAM 8 GB).
- **Akibat.** T = 30 dipilih sebagai T kedua untuk perbandingan fusion, karena deteksinya jelas lebih baik dan biayanya masih terjangkau.
- **Rincian.** `Temuan_Data_dan_Sweep_T.md` bagian 11–17, `Ringkasan_Sweep_T_untuk_Dosen.md`.

### E8. Seed tambahan 31 dan 2026 (22 November)

- **Masalah.** E2 menunjukkan CI n = 3 terlalu lebar untuk membedakan fusion.
- **Yang dilakukan.** Menambah seed 31 dan 2026 untuk F1 dan F2 di T = 10. Semua perbandingan fusion selanjutnya memakai 5 seed.
- **Hasil.** Kesimpulan n = 3 untuk F2 vs F1 sebagian berubah, dan kesimpulan n = 5 menggantikannya.
- **Rincian.** `Laporan_Fusion_F1_vs_F2.md` bagian 9.

### E9. F3: Gated Multimodal Unit di T = 10 (23 November)

- **Masalah.** Lanjutan E6. F1 punya satu gate setelah ketiga modalitas dicampur, sehingga tidak bisa membedakan modalitas. GMU memberi **gate tersendiri untuk tiap modalitas** (trace, log, metric), dihitung dari ketiganya, sebelum digabung. Hipotesisnya: model bisa meredam modalitas yang "ramai" pada jendela normal, sehingga alarm palsu berkurang.
- **Yang dilakukan.** Implementasi GMU sesuai Arevalo dkk. (2017), versi tiga modalitas, tanpa bias (`Eadro/codes/model.py:211`). T = 10, 5 seed, kedua skema.
- **Hasil.** F3 setara atau sedikit lebih baik dari F1. Dua selisih lolos, keduanya tipis: HR@1 `within_event` +0,042 dan F1(std) `leave_event_out` +0,059 (CI +0,001 s.d. +0,116). Tapi F3 punya **28% lebih banyak parameter total** (fusion 36.864 vs 18.560).
- **Akibat.** Perlu diuji di T kedua (→ E11, E12). Masalah kapasitas dicatat sebagai keterbatasan (→ E13).
- **Rincian.** `docs/F3_GMU.md`, `Laporan_Fusion_F1_vs_F2.md` bagian 10.

### E10. Cek jumlah epoch di T = 30 (24 November)

- **Masalah.** Di sweep T, banyak run memilih epoch 14, yaitu evaluasi terakhir. Mungkin 15 epoch belum cukup untuk T = 30.
- **Yang dilakukan.** F1 seed 42, T = 30, 30 epoch, kedua skema.
- **Hasil.** `within_event` puncak di epoch 9 (15 epoch cukup). `leave_event_out` Val combo terus naik sampai epoch 29 (0,790).
- **Akibat.** Fusion T = 30 `within_event` memakai 15 epoch, `leave_event_out` memakai **30 epoch**. Konsekuensinya, T = 10 `leave_event_out` (15 epoch) dan T = 30 `leave_event_out` (30 epoch) berbeda dua hal sekaligus (→ E14).
- **Rincian.** `Perbandingan_Seluruh_Eksperimen.md` bagian 5.8.

### E11. Fusion F1/F2/F3 di T = 30, `within_event` (24 November)

- **Masalah.** Apakah pola fusion di T = 10 berulang di T lain?
- **Yang dilakukan.** F1, F2, F3, 5 seed, 15 epoch.
- **Hasil.** Ketiganya setara. Selisih antar fusion (paling besar +0,035) lebih kecil daripada selisih karena T.
- **Rincian.** `Laporan_Fusion_F1_vs_F2.md` bagian 11.

### E12. Fusion F1/F2/F3 di T = 30, `leave_event_out` (25 November)

- **Masalah.** Sama dengan E11, untuk skema yang lebih ketat.
- **Yang dilakukan.** F1, F2, F3, 5 seed, 30 epoch.
- **Hasil.** **F3 lebih baik dalam deteksi**: F1(std) 0,910 vs 0,849 (F1) dan 0,850 (F2). Sumbernya alarm palsu: FPR 0,240 vs 0,439 dan 0,492, lebih rendah di kelima seed. HR@1 tidak berbeda. Terhadap F1, turunnya FPR oleh F3 juga muncul di T = 10 `leave_event_out` dengan besar yang mirip. Ini selisih fusion pertama yang berulang di dua T.
- **Akibat.** Muncul pertanyaan: F3 unggul karena **mekanisme gating-nya**, atau hanya karena **parameternya dua kali lipat**? Keterbatasan #2 di `Laporan_Fusion_F1_vs_F2.md` §12.7 menyebut ini secara eksplisit (→ E13).
- **Rincian.** `Laporan_Fusion_F1_vs_F2.md` bagian 12.

### E13. F1w: kapasitas atau mekanisme? (25–26 November)

#### Masalah awal

Setelah E12, klaim "GMU lebih baik" belum bisa dipertahankan. F3 berbeda dari F1 dalam **dua hal sekaligus**:

| | F1 | F3 |
|---|---|---|
| Arsitektur fusion | concat → Linear → GLU (satu gate setelah pencampuran) | gate per modalitas, sebelum pencampuran |
| Parameter fusion | 18.560 | 36.864 (**2×**) |

Kalau F3 lebih baik, penyebabnya bisa arsitekturnya, bisa juga sekadar karena modelnya lebih besar. Reviewer pasti menanyakan ini. Satu-satunya cara memisahkan keduanya: buat F1 yang **ukurannya sama dengan F3** tapi arsitekturnya tetap F1.

#### Yang dilakukan

**Desain F1w** (`ConcatGLUWide`, `Eadro/codes/model.py`):

```
F1 : concat(trace, log, metric) → Linear(144 → 128) → GLU → 64
F1w: concat(trace, log, metric) → Linear(144 → 135) → ReLU → Linear(135 → 128) → GLU → 64
```

- Ditambah satu lapisan tersembunyi berukuran 135 supaya parameter fusion = **36.983**, hampir sama dengan F3 (**36.864**, selisih 0,3%).
- Tahap keluarannya tetap GLU yang sama dengan F1: satu gate bersama, dipasang setelah pencampuran. Jadi **arsitektur gating F1 tidak berubah, hanya kapasitasnya**.
- ReLU di antara dua Linear wajib. Tanpa ReLU, dua Linear berturut-turut setara dengan satu Linear (berperingkat rendah), sehingga tidak ada kapasitas tambahan.

**Cara membaca hasilnya:**

| Selisih | Artinya |
|---|---|
| F1w − F1 | efek **kapasitas** saja (arsitektur sama) |
| F3 − F1w | efek **arsitektur GMU** (kapasitas sama) |

**Run.** 15 run, 5 seed (42, 7, 123, 31, 2026), pengaturan sama persis dengan pasangan F1/F2/F3-nya:

| Setting | Epoch | Hash (urut seed) | Log |
|---|---|---|---|
| T = 10, `leave_event_out` | 15 | `6cf6f409`, `434b55ff`, `aaf0ec9e`, `4799642d`, `e6d6338f` | `grid_T10_f1w_leo.out` |
| T = 10, `within_event` | 15 | `5a627171`, `26470543`, `eeef59a4`, `cc6edef8`, `8d78dd3b` | `grid_T10_f1w_we.out` |
| T = 30, `leave_event_out` | 30 | `16489783`, `28c0b120`, `a5f15a29`, `cdb5d35c`, `1f6c0ac2` | `grid_T30_f1w_leo.out` |

Rekap: `work/envs/train312/bin/python -I pipeline/banding_fusion.py 10 15` dan `... banding_fusion.py 30 30 leave_event_out`.

#### Hasil efektivitas

Δ = F3 − F1w. ✱ = CI 95% Welch tidak memuat 0. p = uji permutasi dua sisi (252 pembagian).

**T = 10, `within_event`: tidak ada perbedaan**

| Metrik | F1 | F1w | F3 | Δ | p |
|---|---|---|---|---|---|
| F1(std) | 0,763 ± 0,014 | 0,778 ± 0,038 | 0,808 ± 0,064 | +0,030 | 0,41 |
| HR@1 | 0,814 ± 0,024 | 0,836 ± 0,053 | 0,856 ± 0,022 | +0,020 | 0,53 |
| FPR | 0,618 ± 0,112 | 0,601 ± 0,133 | 0,534 ± 0,238 | −0,067 | 0,55 |

**T = 10, `leave_event_out`: F1w menyamai F3 dalam deteksi, lebih baik dalam lokalisasi**

| Metrik | F1 | F1w | F3 | Δ | p |
|---|---|---|---|---|---|
| F1(std) | 0,800 ± 0,047 | 0,855 ± 0,020 | 0,858 ± 0,014 | +0,003 | 0,75 |
| Precision | 0,720 ± 0,054 | 0,770 ± 0,034 | 0,793 ± 0,027 | +0,023 | 0,26 |
| FPR | 0,535 ± 0,132 | 0,439 ± 0,087 | 0,371 ± 0,067 | −0,067 | 0,21 |
| HR@1 | 0,582 ± 0,118 | **0,667 ± 0,044** | 0,605 ± 0,029 | **−0,062 ✱** | 0,024 |
| NDCG@3 | 0,650 ± 0,110 | 0,742 ± 0,049 | 0,683 ± 0,025 | −0,059 | 0,048 |
| HR@1 bersyarat | 0,641 ± 0,090 | 0,692 ± 0,046 | 0,645 ± 0,028 | −0,047 | 0,048 |

**T = 30, `leave_event_out` (30 epoch): F3 unggul, F1w = F1**

| Metrik | F1 | F1w | F3 | Δ | p |
|---|---|---|---|---|---|
| F1(std) | 0,849 ± 0,039 | 0,850 ± 0,041 | **0,910 ± 0,020** | **+0,060 ✱** | 0,024 |
| Precision | 0,784 ± 0,033 | 0,785 ± 0,047 | **0,872 ± 0,024** | **+0,087 ✱** | 0,016 |
| FPR | 0,439 ± 0,068 | 0,438 ± 0,116 | **0,240 ± 0,050** | **−0,199 ✱** | 0,016 |
| HR@3 | 0,651 ± 0,034 | 0,661 ± 0,054 | 0,750 ± 0,058 | +0,089 ✱ | 0,040 |
| HR@1 | 0,560 ± 0,064 | 0,559 ± 0,067 | 0,599 ± 0,063 | +0,040 | 0,47 |

F1(std) F3 per seed 0,879–0,925, FPR semua ≤ 0,33. F1w per seed 0,785–0,889, FPR 0,31–0,62.

#### Hasil efisiensi

Waktu dirata-rata dari 5 seed, laptop i7-8650U (CPU).

| Setting | Fusion | Param total | Param fusion | Inferensi (ms/jendela) | Latih (s/epoch) | RAM puncak (MB) |
|---|---|---|---|---|---|---|
| T = 10 `within_event` | F1 | 66.050 | 18.560 | 0,267 | 50,7 | 2.753 |
| | F1w | 84.473 | 36.983 | 0,274 (+2%) | 50,8 (+0%) | 2.752 |
| | F3 | 84.354 | 36.864 | 0,286 (+7%) | 53,5 (+6%) | 2.752 |
| T = 10 `leave_event_out` | F1 | 66.050 | 18.560 | 0,268 | 57,8 | 2.788 |
| | F1w | 84.473 | 36.983 | 0,268 (+0%) | 57,9 (+0%) | 2.786 |
| | F3 | 84.354 | 36.864 | 0,284 (+6%) | 60,5 (+5%) | 2.787 |
| T = 30 `leave_event_out` | F1* | 68.650 | 18.560 | 0,877 | 143,7 | 5.314 |
| | F1w | 87.073 | 36.983 | 0,888 (+1%) | 143,7 (+0%) | 5.315 |
| | F3 | 86.954 | 36.864 | 0,897 (+2%) | 144,9 (+1%) | 5.315 |

\* Tanpa seed 42 (`14f5c50b`, run cek epoch E10). Run itu lambat (215 s/epoch, 1,41 ms/jendela), kemungkinan karena berjalan bersamaan dengan proses lain. Seed lain sekitar 143 s/epoch.

- Menggandakan parameter fusion (F1 → F1w) **hampir tidak menambah biaya**. Sebagian besar komputasi ada di encoder, bukan di fusion.
- F3 sedikit lebih mahal dari F1w walau parameternya sama: +5–7% di T = 10, +1–2% di T = 30. Kemungkinan karena GMU punya lebih banyak operasi terpisah (tiga proyeksi tanh, gate sigmoid, penjumlahan berbobot). Di T = 30 selisihnya tertutup oleh encoder yang lebih berat.
- RAM ditentukan oleh T, bukan oleh fusion.

#### Kesimpulan

1. **T = 30 `leave_event_out`: keunggulan F3 berasal dari arsitektur GMU, bukan dari kapasitas.** Menambah parameter ke F1 tidak mengubah apa pun (F1w = F1). Sebaliknya, pada kapasitas yang sama F3 menaikkan F1(std) +0,060 dan memotong alarm palsu hampir setengahnya, dengan tambahan biaya hanya 1–2%.
2. **T = 10: keunggulan F3 atas F1 cukup dijelaskan oleh kapasitas.** Begitu F1 diperbesar, deteksinya menyamai F3. Di `leave_event_out` F1w malah lebih baik dalam lokalisasi (HR@1 +0,062 terhadap F3).
3. **Yang mengubah laporan sebelumnya.** `Laporan_Fusion_F1_vs_F2.md` §12.6 menulis "lokalisasi tidak berbeda antar fusion, di T dan skema mana pun". Dengan F1w, ada satu pengecualian: T = 10 `leave_event_out`, F1w > F3 untuk HR@1. Klaim "F3 lebih baik dari F1 di T = 10 `leave_event_out`" (E9) juga harus diberi catatan: selisih itu hilang setelah kapasitas disamakan.

#### Keterbatasan

1. **Efek T bercampur dengan efek epoch.** Di `leave_event_out`, T = 10 dilatih 15 epoch dan T = 30 dilatih 30 epoch (E10). Jadi "GMU unggul di T = 30 tapi tidak di T = 10" bisa juga berarti "GMU unggul kalau dilatih lebih lama" (→ dijawab E14).
2. **"Arsitektur GMU" masih satu paket.** GMU berbeda dari F1w dalam tiga hal: proyeksi terpisah per modalitas, gate per modalitas yang bergantung input, dan penggabungan lewat penjumlahan berbobot. Belum diketahui komponen mana yang bekerja (→ R3, R4).
3. **Banyak pengujian tanpa koreksi.** Dengan 5 vs 5 seed, p terkecil yang mungkin ≈ 0,008. Hasil dengan p ≈ 0,04–0,05 (NDCG@3, HR@1 bersyarat di T = 10 `leave_event_out`) sebaiknya disebut indikasi. Temuan T = 30 lebih kuat karena F1, Precision, dan FPR kompak.
4. **Pemilihan epoch F1w kadang sangat awal** (mis. seed 31 di T = 30 memilih epoch 4). Itu hasil seleksi Val, bukan bug, tetapi menandakan Val combo F1w kurang stabil.
5. Satu pembagian event, satu dataset (TT), satu mesin.

### E14. Kontrol epoch: T = 10 `leave_event_out` dengan 30 epoch (26–27 November)

- **Masalah.** Keterbatasan E13 #1. Di `leave_event_out`, T = 10 dilatih 15 epoch, sedangkan T = 30 dilatih 30 epoch. Akibatnya kesimpulan "F3 unggul di T = 30, tidak di T = 10" bisa disebabkan oleh T, bisa juga oleh lama training. Eksperimen ini hanya mengubah epoch untuk memisahkan keduanya. Tujuannya **bukan** membuktikan bahwa efeknya dari GMU (itu sudah dijawab E13 lewat F3 vs F1w), melainkan mencari **dalam kondisi apa** efek itu muncul.
- **Yang dilakukan.** F1, F1w, F2, F3; T = 10 `leave_event_out`, **30 epoch**, 5 seed (42, 7, 123, 31, 2026), 20 run, ±32 menit per run. Pengaturan lain sama dengan E13. Log: `grid_T10_30ep_leo.out`. Hash F1: `ce19011a 61f1babc 73d84a2f 636326be ee152c1b`; F1w: `101631d3 cd43eaca f457e1ae f35a159e 0c4741ab`; F2: `6d1ac50c d5734579 fc258582 7bd38b07 e98e716e`; F3: `cae8ee1f 2cb875ec e6c38f8e a43a7ae2 0f464d2e`.
- **Perbaikan skrip.** Rekap pertama memuat 6 run F1 karena ada run lama `d574273b` (F1 seed 42, 30 epoch, pemilihan epoch pakai kriteria `HR@1`, bukan `combo`). `pipeline/banding_fusion.py` sekarang hanya mengambil run dengan `select_metric = combo`. Konfigurasi lain tidak terdampak (sudah dicek: run `HR@1` lain hanya ada di setting 50 epoch lama).
- **Hasil 1: F3 ≈ F1w juga pada 30 epoch.**

  | Metrik | F1 | F1w | F2 | F3 | F3 − F1w [CI 95%] | p |
  |---|---|---|---|---|---|---|
  | F1(std) | 0,805 ± 0,044 | 0,853 ± 0,025 | 0,831 ± 0,038 | 0,844 ± 0,022 | −0,009 [−0,043; +0,026] | 0,59 |
  | Precision | 0,742 ± 0,064 | 0,786 ± 0,019 | 0,783 ± 0,048 | 0,796 ± 0,016 | +0,011 [−0,016; +0,037] | 0,38 |
  | FPR | 0,471 ± 0,148 | 0,384 ± 0,036 | 0,377 ± 0,109 | 0,348 ± 0,040 | −0,036 [−0,092; +0,020] | 0,19 |
  | HR@1 | 0,572 ± 0,083 | 0,650 ± 0,056 | 0,537 ± 0,094 | 0,577 ± 0,067 | −0,073 [−0,165; +0,018] | 0,10 |
  | HR@3 | 0,687 ± 0,087 | 0,764 ± 0,062 | 0,648 ± 0,096 | 0,720 ± 0,052 | −0,044 [−0,128; +0,039] | 0,27 |

  Tidak ada selisih antar-fusion yang CI-nya tidak memuat 0, kecuali Recall F1w − F1 (+0,052, p = 0,056). F3 − F1 untuk F1(std) turun dari +0,059 ✱ (15 epoch) menjadi +0,039 (p = 0,12).
- **Hasil 2: 30 epoch tidak mengubah apa pun di T = 10.** Selisih 30 − 15 epoch per fusion (CI Welch, p permutasi): F1(std) F1 +0,005 (p = 0,87), F1w −0,002 (0,82), F2 +0,007 (0,75), F3 −0,014 (0,26). FPR semua turun sedikit (−0,02 s.d. −0,07), tidak ada yang signifikan (p ≥ 0,25). Epoch terpilih Val tersebar 9–29. Jadi baseline T = 10 `leave_event_out` dengan 15 epoch **tidak kurang dilatih**.
- **Hasil 3: perbandingan T = 10 vs T = 30 pada epoch yang sama (30).**

  | Fusion | F1(std) T = 10 | F1(std) T = 30 | FPR T = 10 | FPR T = 30 |
  |---|---|---|---|---|
  | F1 | 0,805 | 0,849 | 0,471 | 0,439 |
  | F1w | 0,853 | 0,850 | 0,384 | 0,438 |
  | F3 | 0,844 | **0,910** | 0,348 | **0,240** |

  F1w tidak mendapat apa-apa dari jendela yang lebih panjang. F3 justru paling banyak terbantu. Catatan: T = 10 dan T = 30 memakai himpunan jendela uji yang berbeda, jadi tabel ini deskriptif, bukan uji berpasangan.
- **Efisiensi.** Sama dengan E13: ±57–59 s/epoch, 0,26–0,28 ms/jendela, RAM ±2,8 GB. Biaya 30 epoch dua kali lipat tanpa hasil.
- **Akibat.**
  1. Sesuai tabel baca yang disusun sebelum run (rencana R2 lama): **keunggulan GMU atas F1w bergantung pada T, bukan pada lama training.** Klaim "gating GMU baru berguna saat jendela panjang (T = 30)" boleh dipakai, dengan catatan baru dua titik T (→ R5 kalau ingin tren).
  2. Kesimpulan E13 #2 ("T = 10: cukup dijelaskan kapasitas") **makin kuat**: dengan 30 epoch, F3 bahkan tidak lagi signifikan terhadap F1.
  3. Pengecualian lokalisasi di E13 (F1w > F3 untuk HR@1 di T = 10 `leave_event_out`) **melemah**: arahnya sama (−0,073) tetapi p = 0,10. Sebut sebagai indikasi, bukan temuan.
  4. Fusion T = 10 di eksperimen berikutnya (R1) tetap memakai 15 epoch.
- **Rincian.** `work/envs/train312/bin/python -I pipeline/banding_fusion.py 10 30 leave_event_out`.

---

## 3. Status klaim saat ini (27 November)

| Klaim | Bukti | Status |
|---|---|---|
| Selisih ke angka paper berasal dari protokol yang bocor | E4 | kuat |
| Gate GLU di F1 tidak diperlukan | E6, E11, E12: F2 ≈ F1 di 2 T × 2 skema | kuat |
| T lebih besar memperbaiki deteksi, tidak memperbaiki lokalisasi | E7 (n = 3, sebagian besar tidak signifikan) | arah konsisten, belum signifikan |
| F3 mengurangi alarm palsu di event baru (`leave_event_out`) | E9, E12 | kuat di T = 30; di T = 10 dijelaskan oleh kapasitas (E13, E14) |
| Keunggulan F3 di T = 30 berasal dari arsitektur GMU, bukan kapasitas | E13 | kuat (untuk T = 30 `leave_event_out`, 30 epoch) |
| Keunggulan GMU bergantung pada T, bukan lama training | E13, E14 | kuat untuk T = 10 vs 30 (dua titik T saja) |
| 15 epoch cukup untuk T = 10 `leave_event_out` | E14 | kuat (30 epoch tidak mengubah fusion mana pun) |
| Komponen GMU yang bekerja adalah gating adaptif | — | **belum diuji** (R3, R4) |
| Fusion tidak memperbaiki lokalisasi | E9–E14 | sebagian besar benar; F1w > F3 untuk HR@1 di T = 10 `leave_event_out` hanya indikasi (p = 0,024 di 15 epoch, 0,10 di 30 epoch) |

---

## 4. Rencana berikutnya (belum dijalankan)

Keputusan dosen (25 November): **paper berupa studi perbandingan fusion**. Ablasi khusus GMU disimpan untuk kemungkinan paper terpisah. Urutan di bawah mengikuti keputusan itu.

### R1. Fusion tambahan: `sum`, `attn`, `lmf`

- **Masalah.** Studi perbandingan baru punya F1, F2, F3 (dan F1w sebagai kontrol). Tiga varian sudah ada di kode (`Eadro/codes/model.py:161`) tetapi belum pernah dijalankan.
- **Desain.** Pengaturan sama dengan F1/F2/F3: T = 10 (15 epoch) dan T = 30 `leave_event_out` (30 epoch), 5 seed. Catat parameter fusion tiap varian. Kalau ada varian yang jauh lebih besar atau kecil, F1w dan F2 sudah menjadi pembanding kapasitas.
- **Biaya.** Per varian: T = 10 dua skema ±2,7 jam, T = 30 `leave_event_out` ±6 jam.

### R3. Analisis nilai gate GMU (tanpa training)

- **Masalah.** Keterbatasan E13 #2, dan dugaan di `Laporan_Fusion_F1_vs_F2.md` §12.6 bahwa GMU meredam modalitas yang ramai pada jendela normal belum pernah dicek.
- **Desain.** Muat `model.ckpt` F3 (T = 10 dan T = 30), baca `last_gates` di data Test. Lihat: apakah gate bervariasi antar sampel, apakah berbeda antara jendela normal dan jendela gangguan atau antar jenis gangguan, dan apakah gate di T = 30 lebih selektif daripada di T = 10.
- **Sifat bukti.** Deskriptif, untuk bagian diskusi. Bukan bukti kausal.

### R4. Ablasi GMU dengan gate statis (prioritas rendah, untuk paper GMU)

- **Masalah.** Memisahkan "gating adaptif" dari "proyeksi per modalitas".
- **Desain.** Varian `gmu_static`: `z_i = sigmoid(b_i)` (bobot per modalitas yang dipelajari, tetapi sama untuk semua sampel). Komponen lain identik dengan F3. T = 30 `leave_event_out`, 30 epoch, 5 seed.
- **Cara membaca.** Kalau `gmu_static` ≈ F3, yang bekerja adalah proyeksi per modalitas. Kalau `gmu_static` ≈ F1w dan lebih buruk dari F3, yang bekerja adalah gating adaptif. Parameternya lebih sedikit dari F3, tetapi E13 menunjukkan kapasitas tidak berpengaruh di setting ini.
- **Biaya.** ±6 jam. Perlu menambah kelas baru di `model.py`.

### R5. T = 50 `leave_event_out` (opsional)

- **Masalah.** Tren "GMU makin berguna saat T makin besar" baru punya dua titik.
- **Desain.** Fusion yang relevan, 5 seed, **30 epoch** (data E7 menunjukkan 15 epoch belum konvergen). T = 60 dilewati karena F1 sudah mendatar di T = 50 dan biayanya ±25% lebih mahal.
- **Biaya.** ±2,1 jam per run (F1w + F3 saja: ±21 jam; empat fusion: ±42 jam). RAM ±7,6 GB, jadi tidak bisa dijalankan paralel.

---

## 5. Format entri baru

```markdown
### E<n>. <judul singkat> (<tanggal>)

- **Masalah.** Kenapa eksperimen ini perlu. Rujuk keterbatasan atau entri sebelumnya yang memicunya.
- **Yang dilakukan.** Varian, T, skema, epoch, seed, jumlah run. Hash dan berkas log.
- **Hasil.** Angka utama (rata-rata ± sd, selisih, CI/p). Efisiensi bila relevan.
- **Akibat.** Apa yang berubah pada klaim (bagian 3) dan eksperimen apa yang dipicunya.
- **Rincian.** Laporan dan skrip rekap.
```
