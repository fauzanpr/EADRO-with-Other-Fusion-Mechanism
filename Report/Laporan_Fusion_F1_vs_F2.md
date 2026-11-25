# Laporan Perbandingan Fusion: F1 (`concat_glu`) vs F2 (`concat_fc`) vs F3 (`gmu`)

| | |
|---|---|
| Tanggal | 16 November 2026 |
| Data | Train Ticket (TT), `A1`, jendela T = 10 detik |
| Protokol | `within_event` dan `leave_event_out` |
| Pengaturan | 15 epoch, batch 256, lr 0,001, epoch dipilih dengan `combo` = (F1(std) + HR@1(std))/2 di Val, evaluasi tiap 5 epoch |
| Seed | 42, 7, 123 (bagian 1–8, 16 November) dan tambahan 31, 2026 (bagian 9, 22 November). **Bagian 9 menggantikan kesimpulan n = 3.** F3: kelima seed sejak awal (bagian 10, 23 November) |
| Perbedaan antar varian | Hanya modul fusion. Data, kode, environment, dan hyperparameter lain identik (dicek lewat `params.json` dan tanggal berkas) |
| Perintah F2 | `pipeline/run_grid.sh within_event 15 "42 7 123" "concat_fc"` dan `pipeline/run_grid.sh leave_event_out 15 "42 7 123" "concat_fc"` |
| Perintah F3 | `pipeline/run_grid.sh within_event 15 "42 7 123 31 2026" "gmu"` lalu `leave_event_out` (keluaran `grid_gmu.out`) |
| Rekap | `work/envs/train312/bin/python pipeline/rekap_seed.py work/result`; F1/F2/F3: `work/envs/train312/bin/python -I pipeline/banding_fusion.py [T] [epoch] [skema]` (tanpa argumen: T = 10, kedua skema) |
| T = 30 | Bagian 11 (24 November): `within_event`, 15 epoch, 5 seed. Bagian 12 (25 November): `leave_event_out`, 30 epoch, 5 seed |

Angka F1 berasal dari run baseline yang sama di `Laporan_Eksperimen_Seed.md` dan `Laporan_Efisiensi_F1.md`.

> **Pembaruan 25 November (T = 30 `leave_event_out`, lihat bagian 12).** Di skema event baru, F3 **lebih baik dari F1 dan F2 untuk deteksi**: F1(std) 0,910 vs 0,849 / 0,850 (+0,061, CI +0,013 s.d. +0,109 terhadap F1; +0,060, CI +0,010 s.d. +0,110 terhadap F2). Sumbernya alarm palsu yang jauh lebih sedikit: FPR 0,240 vs 0,439 / 0,492, lebih rendah di kelima seed. Lokalisasi (HR@1(std)) tidak berbeda (0,599 vs 0,560 / 0,591). F2 tetap setara F1. Pengurangan alarm palsu F3 terhadap F1 di `leave_event_out` sekarang muncul di T = 10 dan T = 30. Ini selisih fusion pertama yang berulang di dua T.

> **Pembaruan 24 November (T = 30 `within_event`, lihat bagian 11).** Di T = 30, ketiga fusion setara untuk deteksi dan lokalisasi. F2 − F1 tinggal +0,009 di F1(std), jadi petunjuk F2 di T = 10 tidak berulang. F3 cenderung lebih sedikit alarm palsu (FPR 0,36 vs 0,53, belum terbukti) dan HR@1 bersyaratnya sedikit lebih tinggi (+0,023, CI +0,003 s.d. +0,043). Keunggulan HR@1(std) F3 di T = 10 tidak berulang (+0,004). `leave_event_out` T = 30 belum dijalankan.

> **Pembaruan 23 November (F3 = GMU, lihat bagian 10).** F3 setara atau sedikit lebih baik dari F1: semua selisih rata-rata searah menguntungkan F3, tetapi hanya dua yang CI-nya tidak memuat 0, dan keduanya tipis (HR@1(std) `within_event` +0,042; F1(std) `leave_event_out` +0,059). Terhadap F2 tidak ada selisih terbukti. F3 memakai 28% parameter lebih banyak dari F1.

> **Pembaruan 22 November (5 seed, lihat bagian 9).** Dua seed tambahan (31, 2026) **membalik** kesimpulan lokalisasi di bagian 4 dan 7. Dengan n = 5, selisih HR@1(std) di `leave_event_out` hanya −0,049 (CI 95% −0,197 s.d. +0,099) dan arahnya tidak lagi konsisten (F2 lebih tinggi di 2 dari 5 seed). Klaim "GLU membantu lokalisasi pada event baru" **tidak didukung data**. Satu-satunya selisih yang CI-nya tidak melewati nol adalah F1(std) di `within_event`: F2 lebih tinggi +0,043 (CI +0,005 s.d. +0,081), tepat di batas.

**Ringkasan (n = 3, 16 November, sebagian digantikan):** Di `within_event` (event yang sudah pernah dilihat), F2 setara atau sedikit lebih baik dari F1. Di `leave_event_out` (event baru), F2 tetap mengurangi alarm palsu, tetapi ~~lokalisasinya jelas lebih buruk (HR@1(std) −0,14, konsisten di ketiga seed)~~ (digantikan bagian 9). ~~GLU tidak berpengaruh pada event yang dikenal, tetapi membantu lokalisasi pada event baru.~~

---

## 1. Perbedaan arsitektur

| | F1 `concat_glu` (EADRO asli) | F2 `concat_fc` (ablation tanpa GLU) |
|---|---|---|
| Alur fusion | gabung 3 modalitas (144) → FC 144→128 → GLU → 64 | gabung 3 modalitas (144) → FC 144→64 → ReLU |
| Parameter fusion | 18.560 | 9.280 (−50%) |
| Parameter total | 66.050 | 56.770 (−14%) |

GLU (*Gated Linear Unit*) membagi keluaran FC menjadi dua bagian. Satu bagian menjadi "gerbang" (sigmoid) yang menentukan seberapa banyak bagian lain diteruskan. F2 menghapus gerbang ini dan hanya memakai satu lapisan FC biasa dengan ReLU.

---

## 2. Data dan daftar run

| Protokol | Train | Val | Test | Test: gangguan / normal |
|---|---|---|---|---|
| `within_event` | 40.510 | 7.490 | 32.190 | 17.990 / 14.200 |
| `leave_event_out` | 46.160 | 7.695 | 27.352 | 16.452 / 10.900 |

| Protokol | Fusion | Seed | Hash | Epoch terpilih | Val combo |
|---|---|---|---|---|---|
| `within_event` | `concat_glu` | 42 | `fb3e4cc0` | 14 | 0,9431 |
| `within_event` | `concat_glu` | 7 | `74f2db5a` | 14 | 0,9495 |
| `within_event` | `concat_glu` | 123 | `dc38d8d0` | 9 | 0,9476 |
| `within_event` | `concat_fc` | 42 | `24bacc97` | 14 | 0,9623 |
| `within_event` | `concat_fc` | 7 | `db7b1118` | 9 | 0,9610 |
| `within_event` | `concat_fc` | 123 | `15fa7e10` | 9 | 0,9807 |
| `leave_event_out` | `concat_glu` | 42 | `97e94b9a` | 14 | 0,7375 |
| `leave_event_out` | `concat_glu` | 7 | `a8af9989` | 14 | 0,7607 |
| `leave_event_out` | `concat_glu` | 123 | `9e7dfa9a` | 9 | 0,7666 |
| `leave_event_out` | `concat_fc` | 42 | `1c24707e` | 14 | 0,7364 |
| `leave_event_out` | `concat_fc` | 7 | `d8fbfd18` | 14 | 0,7599 |
| `leave_event_out` | `concat_fc` | 123 | `34e93f90` | 14 | 0,7791 |

---

## 3. Hasil `within_event` (Test, epoch terpilih)

### 3.1 Rata-rata ± sd (n = 3)

| Ukuran | F1 `concat_glu` | F2 `concat_fc` | Selisih rata-rata |
|---|---|---|---|
| F1(std) | 0,767 ± 0,017 | **0,818 ± 0,031** | +0,051 |
| Precision(std) | 0,658 ± 0,045 | **0,736 ± 0,040** | +0,078 |
| Recall(std) | 0,923 ± 0,037 | 0,923 ± 0,034 | −0,001 |
| HR@1(std) | 0,822 ± 0,031 | 0,842 ± 0,042 | +0,021 |
| HR@3(std) | 0,883 ± 0,024 | 0,890 ± 0,038 | +0,007 |
| HR@5(std) | 0,896 ± 0,027 | 0,900 ± 0,034 | +0,004 |
| NDCG@3(std) | 0,858 ± 0,027 | 0,871 ± 0,040 | +0,013 |
| NDCG@5(std) | 0,864 ± 0,027 | 0,875 ± 0,038 | +0,011 |
| F1 (asli) | 0,813 ± 0,029 | 0,870 ± 0,028 | +0,057 |
| HR@1 (asli) | 0,634 ± 0,064 | 0,579 ± 0,026 | −0,055 |

"(std)" = metrik standar yang hanya menghitung kelas gangguan. Gangguan yang tidak terdeteksi dihitung sebagai meleset untuk HR@k dan NDCG@k. "(asli)" = rumus kode EADRO asli. HR@1 asli turun karena cacat rumusnya: model yang alarm palsunya lebih sedikit justru mendapat HR@1 asli lebih rendah (lihat `Laporan_Tingkat_A_Protokol_Asli.md`). **Perbandingan memakai versi (std).**

### 3.2 Per seed

| Seed | Fusion | Epoch | F1(std) | Pre(std) | Rec(std) | HR@1(std) | HR@3(std) | NDCG@3(std) |
|---|---|---|---|---|---|---|---|---|
| 42 | `concat_glu` | 14 | 0,786 | 0,710 | 0,881 | 0,809 | 0,865 | 0,842 |
| 42 | `concat_fc` | 14 | 0,782 | 0,694 | 0,897 | 0,797 | 0,852 | 0,830 |
| 7 | `concat_glu` | 14 | 0,758 | 0,632 | 0,946 | 0,857 | 0,911 | 0,889 |
| 7 | `concat_fc` | 9 | 0,836 | 0,774 | 0,910 | 0,848 | 0,889 | 0,872 |
| 123 | `concat_glu` | 9 | 0,757 | 0,632 | 0,943 | 0,799 | 0,873 | 0,843 |
| 123 | `concat_fc` | 9 | 0,837 | 0,740 | 0,962 | 0,882 | 0,927 | 0,909 |

### 3.3 Selisih berpasangan (F2 − F1, seed yang sama)

| Ukuran | Seed 42 | Seed 7 | Seed 123 | Rata-rata |
|---|---|---|---|---|
| F1(std) | −0,004 | +0,079 | +0,079 | +0,051 |
| Precision(std) | −0,017 | +0,142 | +0,108 | +0,078 |
| Recall(std) | +0,017 | −0,037 | +0,018 | −0,001 |
| HR@1(std) | −0,012 | −0,009 | +0,083 | +0,021 |
| HR@3(std) | −0,013 | −0,022 | +0,054 | +0,007 |
| NDCG@3(std) | −0,012 | −0,017 | +0,067 | +0,013 |

### 3.4 Alarm palsu dan gangguan terlewat (turunan)

Dihitung dari Precision dan Recall: TP = Rec × n_gangguan, FP = TP × (1/Pre − 1), FPR = FP / n_normal, FN = n_gangguan − TP.

| Seed | Fusion | Alarm palsu (FP) | FPR | Gangguan terlewat (FN) |
|---|---|---|---|---|
| 42 | `concat_glu` | 6.460 | 45,5% | 2.144 |
| 42 | `concat_fc` | 7.132 | 50,2% | 1.846 |
| 7 | `concat_glu` | 9.924 | 69,9% | 968 |
| 7 | `concat_fc` | 4.781 | 33,7% | 1.626 |
| 123 | `concat_glu` | 9.859 | 69,4% | 1.022 |
| 123 | `concat_fc` | 6.071 | 42,8% | 693 |
| **Rata-rata** | `concat_glu` | 8.748 ± 1.982 | 61,6% ± 14,0% | 1.378 ± 664 |
| **Rata-rata** | `concat_fc` | **5.995 ± 1.177** | **42,2% ± 8,3%** | 1.388 ± 612 |

### 3.5 Pembacaan `within_event`

1. **Deteksi membaik karena alarm palsu berkurang.** Recall identik (0,923), Precision F2 naik 0,078. Rata-rata alarm palsu turun sekitar 2.750 jendela (FPR 62% → 42%).
2. **Lokalisasi setara.** HR@1(std) hanya naik jelas di seed 123 (+0,083). Di seed 42 dan 7 F2 sedikit lebih rendah (−0,01).
3. **Keunggulan F2 belum pasti.** Uji-t berpasangan pada F1(std): t = 1,85 (df = 2), p ≈ 0,2. Seed 42 tidak membaik (−0,004). Pada epoch yang sama untuk semua run (epoch 4), selisihnya mengecil:

   | Ukuran (epoch 4) | F1 | F2 |
   |---|---|---|
   | F1(std) | 0,772 ± 0,016 | 0,798 ± 0,044 |
   | Precision(std) | 0,654 ± 0,036 | 0,690 ± 0,075 |
   | Recall(std) | 0,946 ± 0,026 | 0,953 ± 0,033 |
   | HR@1(std) | 0,809 ± 0,004 | 0,808 ± 0,041 |

4. **Val tidak mewakili Test.** Val combo F2 selalu lebih tinggi (0,95–0,98 vs F1 0,93–0,95), tetapi Val `within_event` jauh lebih mudah daripada Test (sekitar 0,96 vs 0,82).

---

## 4. Hasil `leave_event_out` (Test, epoch terpilih)

### 4.1 Rata-rata ± sd (n = 3)

| Ukuran | F1 `concat_glu` | F2 `concat_fc` | Selisih rata-rata |
|---|---|---|---|
| F1(std) | 0,806 ± 0,036 | 0,827 ± 0,066 | +0,021 |
| Precision(std) | 0,706 ± 0,033 | **0,778 ± 0,042** | +0,072 |
| Recall(std) | **0,938 ± 0,059** | 0,884 ± 0,096 | −0,055 |
| HR@1(std) | **0,650 ± 0,099** | 0,509 ± 0,084 | **−0,141** |
| HR@3(std) | **0,754 ± 0,099** | 0,592 ± 0,084 | **−0,163** |
| HR@5(std) | **0,788 ± 0,087** | 0,659 ± 0,087 | −0,129 |
| NDCG@3(std) | **0,712 ± 0,099** | 0,557 ± 0,085 | **−0,154** |
| NDCG@5(std) | **0,726 ± 0,094** | 0,585 ± 0,086 | −0,141 |
| F1 (asli) | 0,842 ± 0,032 | 0,875 ± 0,049 | +0,033 |
| HR@1 (asli) | 0,513 ± 0,093 | 0,360 ± 0,051 | −0,153 |

### 4.2 Per seed

| Seed | Fusion | Epoch | F1(std) | Pre(std) | Rec(std) | HR@1(std) | HR@3(std) | NDCG@3(std) |
|---|---|---|---|---|---|---|---|---|
| 42 | `concat_glu` | 14 | 0,766 | 0,681 | 0,874 | 0,566 | 0,691 | 0,639 |
| 42 | `concat_fc` | 14 | 0,752 | 0,732 | 0,773 | 0,419 | 0,502 | 0,466 |
| 7 | `concat_glu` | 14 | 0,835 | 0,744 | 0,952 | 0,624 | 0,704 | 0,672 |
| 7 | `concat_fc` | 14 | 0,874 | 0,815 | 0,941 | 0,584 | 0,669 | 0,635 |
| 123 | `concat_glu` | 9 | 0,816 | 0,694 | 0,990 | 0,759 | 0,868 | 0,825 |
| 123 | `concat_fc` | 14 | 0,855 | 0,787 | 0,936 | 0,525 | 0,604 | 0,571 |

### 4.3 Selisih berpasangan (F2 − F1, seed yang sama)

| Ukuran | Seed 42 | Seed 7 | Seed 123 | Rata-rata |
|---|---|---|---|---|
| F1(std) | −0,014 | +0,038 | +0,039 | +0,021 |
| Precision(std) | +0,050 | +0,071 | +0,094 | +0,072 |
| Recall(std) | −0,100 | −0,011 | −0,053 | −0,055 |
| HR@1(std) | −0,148 | −0,040 | −0,235 | −0,141 |
| HR@3(std) | −0,189 | −0,035 | −0,264 | −0,163 |
| NDCG@3(std) | −0,173 | −0,037 | −0,253 | −0,154 |

### 4.4 Alarm palsu, gangguan terlewat, dan lokalisasi bersyarat

HR@1 bersyarat = HR@1(std) / Rec(std), yaitu proporsi layanan penyebab yang benar di posisi 1, **hanya** dari gangguan yang berhasil dideteksi. Ukuran ini memisahkan kualitas lokalisasi dari kualitas deteksi.

| Seed | Fusion | Alarm palsu (FP) | FPR | Gangguan terlewat (FN) | HR@1 bersyarat |
|---|---|---|---|---|---|
| 42 | `concat_glu` | 6.716 | 61,6% | 2.081 | 0,648 |
| 42 | `concat_fc` | 4.659 | 42,7% | 3.733 | 0,542 |
| 7 | `concat_glu` | 5.386 | 49,4% | 790 | 0,656 |
| 7 | `concat_fc` | 3.508 | 32,2% | 967 | 0,620 |
| 123 | `concat_glu` | 7.186 | 65,9% | 169 | 0,767 |
| 123 | `concat_fc` | 4.161 | 38,2% | 1.050 | 0,561 |
| **Rata-rata** | `concat_glu` | 6.430 ± 933 | 59,0% ± 8,6% | 1.013 ± 975 | **0,690** |
| **Rata-rata** | `concat_fc` | **4.109 ± 577** | **37,7% ± 5,3%** | 1.917 ± 1.574 | 0,574 |

### 4.5 Semua epoch yang Test-nya tercatat

Test hanya dihitung ketika Val membaik, jadi tidak semua epoch tercatat. Format: F1(std) / HR@1(std).

| Seed | Fusion | Epoch 4 | Epoch 9 | Epoch 14 |
|---|---|---|---|---|
| 42 | `concat_glu` | 0,774 / 0,524 | 0,786 / 0,621 | 0,766 / 0,566 |
| 42 | `concat_fc` | 0,720 / 0,306 | 0,735 / 0,414 | 0,752 / 0,419 |
| 7 | `concat_glu` | 0,840 / 0,651 | – | 0,835 / 0,624 |
| 7 | `concat_fc` | 0,860 / 0,584 | 0,866 / 0,587 | 0,874 / 0,584 |
| 123 | `concat_glu` | 0,835 / 0,674 | 0,816 / 0,759 | – |
| 123 | `concat_fc` | 0,889 / 0,543 | 0,907 / 0,594 | 0,855 / 0,525 |

Di setiap seed, **HR@1(std) F2 pada epoch terbaiknya masih di bawah HR@1(std) F1 pada epoch terburuknya**: seed 42 0,419 < 0,524, seed 7 0,587 < 0,624, seed 123 0,594 < 0,674.

### 4.6 Val vs Test

| Fusion | HR@1(std) Val (epoch 4 / 9 / 14, rentang 3 seed) | HR@1(std) Test, epoch terpilih |
|---|---|---|
| `concat_glu` | 0,838–0,937 | 0,650 ± 0,099 |
| `concat_fc` | 0,759–0,944 | 0,509 ± 0,084 |

Di Val, lokalisasi kedua varian praktis sama. Perbedaan baru muncul di event Test yang belum pernah dilihat.

### 4.7 Pembacaan `leave_event_out`

1. **Deteksi seimbang.** F2 kembali mengurangi alarm palsu di ketiga seed (FPR 59% → 38%), tetapi lebih banyak gangguan terlewat (Recall −0,055, terbesar di seed 42: −0,100). Keduanya hampir saling menghapus, sehingga F1(std) hanya +0,02. F2 bersikap lebih "hati-hati" dalam menyatakan gangguan.
2. **Lokalisasi F2 jelas lebih buruk.** HR@1(std) turun di ketiga seed (rata-rata −0,141). Penurunan ini tidak hanya akibat lebih banyak gangguan yang terlewat. HR@1 bersyarat juga turun (0,690 → 0,574): ketika F2 berhasil mendeteksi gangguan, ia lebih sering salah menunjuk layanan penyebabnya.
3. **Bukan akibat pemilihan epoch.** Lihat 4.5: epoch terbaik F2 tetap di bawah epoch terburuk F1, di setiap seed.
4. **Kekuatan bukti.** Uji-t berpasangan HR@1(std): t = −2,50 (df = 2), p ≈ 0,13. Secara formal belum signifikan karena n = 3, tetapi arahnya sama di semua seed dan semua epoch. Bukti ini jauh lebih kuat daripada kenaikan F1(std) F2 di `within_event`.
5. **Masalah generalisasi.** Lokalisasi kedua varian sama baiknya di Val (event yang serupa dengan Train), tetapi F2 jatuh lebih dalam di event baru. Dugaan: gerbang GLU membantu model memilih fitur yang lebih umum dari ketiga modalitas, sedangkan FC biasa lebih mudah bergantung pada pola khusus event yang dilatih. Dugaan ini belum diuji langsung.

---

## 5. Ringkasan dua protokol

| Protokol | Deteksi | Lokalisasi |
|---|---|---|
| `within_event` (event sudah pernah dilihat) | F2 sedikit lebih baik: alarm palsu turun, Recall sama (F1(std) +0,05, belum pasti) | Setara (HR@1(std) +0,02) |
| `leave_event_out` (event baru) | Seimbang: alarm palsu turun, gangguan terlewat naik (F1(std) +0,02) | **F1 lebih baik** (HR@1(std) +0,14, konsisten di 3 seed) |

Pola yang konsisten di kedua protokol: **F2 menghasilkan lebih sedikit alarm palsu** (FPR turun sekitar 20 poin persen).

---

## 6. Efisiensi

| Ukuran | `within_event` F1 | `within_event` F2 | `leave_event_out` F1 | `leave_event_out` F2 |
|---|---|---|---|---|
| Parameter fusion | 18.560 | 9.280 | 18.560 | 9.280 |
| Parameter total | 66.050 | 56.770 | 66.050 | 56.770 |
| Detik/epoch | 50,9 ± 0,2 | 51,0 (seed 123)* | 58,5 ± 0,4 | 58,5 ± 0,2 |
| Inferensi (ms/jendela) | 0,268 ± 0,005 | 0,276 (seed 123)* | 0,267 ± 0,003 | 0,270 ± 0,004 |
| Memori puncak (MB) | 2.752 ± 1 | 2.752 ± 1 | 2.788 ± 1 | 2.787 ± 1 |
| Lama run (menit) | 14,8 ± 0,1 | ± 15,0 (seed 123)* | 16,5 ± 0,4 | ± 17,0 |

\* Lihat 6.1.

### 6.1 Catatan kondisi pengukuran `within_event`

Saat seed 42 dan sebagian besar seed 7 F2 `within_event` berjalan, laptop **memakai baterai** (charger tidak terpasang, CPU sekitar 1,2 GHz dalam mode hemat daya). Charger terpasang saat seed 7 di epoch 14.

| Seed F2 `within_event` | Kondisi | Detik/epoch | Inferensi (ms/jendela) |
|---|---|---|---|
| 42 | Baterai | 63,1–67,5 (rata-rata 64,3) | 0,338 |
| 7 | Baterai (epoch 1–13), AC (epoch 14–15) | 62,8–65,3 lalu 51,0–51,2 | 0,271 (diukur di akhir run, sudah AC) |
| 123 | AC penuh | 50,8–51,4 (rata-rata 51,0) | 0,276 |

Karena itu, untuk `within_event` angka waktu F2 yang sebanding dengan F1 hanya dari **seed 123**. Rekap otomatis (`rekap_seed.py`) mencampur ketiga seed (59,1 ± 7,1 s/epoch, 0,295 ± 0,037 ms) dan **tidak boleh dipakai** untuk perbandingan waktu. Untuk `leave_event_out`, ketiga seed F2 memiliki waktu yang stabil dan sama dengan F1 (58,5 s/epoch), jadi bisa dipakai apa adanya.

Training bersifat deterministik di CPU: run `97e94b9a` yang pernah dijalankan dua kali (epoch 1: 104,2 s vs 59,8 s) menghasilkan loss dan metrik Test yang identik sampai digit terakhir. Jadi kondisi baterai hanya memengaruhi angka waktu, **tidak** memengaruhi hasil efektivitas.

### 6.2 Pembacaan efisiensi

Parameter fusion turun 50% dan total turun 14%, tetapi waktu training, waktu inferensi, dan memori praktis sama di kedua protokol. Fusion hanya sebagian kecil dari komputasi. Waktu lebih banyak habis di encoder modalitas, GAT, dan pemuatan data.

---

## 7. Kesimpulan (n = 3; digantikan oleh bagian 9)

> **Catatan 22 November:** bagian ini ditulis dari 3 seed. Klaim lokalisasi di `leave_event_out` (dan "Boleh diklaim" butir kedua) **tidak bertahan** pada 5 seed. Baca bagian 9 untuk kesimpulan yang berlaku. Teks di bawah dibiarkan apa adanya sebagai catatan riwayat analisis.

> Menghapus GLU (F2) memangkas parameter fusion 50% tanpa membuat model lebih cepat. Di kedua protokol, F2 mengurangi alarm palsu (FPR turun sekitar 20 poin persen). Pada event yang sudah dikenal (`within_event`), F2 setara atau sedikit lebih baik dari F1. Pada event baru (`leave_event_out`), **lokalisasi F2 lebih buruk secara konsisten** (HR@1(std) 0,650 → 0,509, turun di ketiga seed dan semua epoch), dan sebagian gangguan lebih sering terlewat. **GLU tidak berpengaruh pada event yang dikenal, tetapi membantu lokalisasi akar masalah pada gangguan yang belum pernah dilihat.**

**Boleh diklaim:**
- F2 menghasilkan lebih sedikit alarm palsu dari F1 di kedua protokol.
- Pada event baru, F1 (dengan GLU) melokalisasi lebih baik dari F2 (arah konsisten di 3 seed, p ≈ 0,13).
- Penghematan parameter F2 tidak menghasilkan percepatan yang terukur.

**Belum boleh diklaim:**
- F2 secara signifikan lebih baik dari F1 (di protokol mana pun).
- Perbedaan lokalisasi di `leave_event_out` signifikan secara statistik (n = 3).
- Penyebab pasti mengapa GLU membantu generalisasi (baru dugaan).

**Pelajaran metodologis:** Hasil `within_event` saja akan mengarah ke kesimpulan "GLU tidak berguna". `leave_event_out` membalik kesimpulan itu untuk lokalisasi. Ini menunjukkan pentingnya menguji varian fusion pada event yang belum pernah dilihat.

---

## 8. Keterbatasan dan tindak lanjut

1. **Jumlah seed kecil (n = 3).** ~~Seed tambahan sebaiknya ditambahkan setelah F3 dan F4 selesai.~~ Sudah dilakukan untuk F1 dan F2 (seed 31 dan 2026, bagian 9) dan terbukti penting: kesimpulan lokalisasi berubah. F3 dan F4 nanti harus memakai kelima seed yang sama.
2. **Angka waktu F2 `within_event` sebagian diukur saat memakai baterai.** Angka final diambil dari skrip benchmark `model.ckpt` yang mengukur semua varian dalam satu sesi (rencana di `Laporan_Efisiensi_F1.md` bagian 6).
3. **`random_original` belum dijalankan untuk F2.** Protokol ini bocor dan baseline-nya hampir mentok, sehingga kurang informatif untuk membandingkan fusion. Rencananya dijalankan di akhir untuk semua varian.
4. **Analisis per jenis gangguan dan per layanan belum dilakukan.** Log hanya menyimpan metrik agregat. Analisis ini memerlukan skrip yang memuat `model.ckpt` dan menyimpan prediksi per jendela, misalnya untuk melihat apakah penurunan lokalisasi F2 terpusat di jenis gangguan tertentu.
5. ~~**F3 dan F4 belum dijalankan.** F3 (Learnable Weighted Feature Fusion: MULAN, Topo-MFP) dan F4 (Cross-Attention: FAMOS) menunggu PDF paper rujukan.~~ F3 sudah dijalankan dengan rujukan baru, Gated Multimodal Unit (Arevalo dkk., 2017), lihat bagian 10. F4 (Cross-Attention: FAMOS) belum.

---

## 9. Pembaruan dengan 5 seed (22 November): kesimpulan yang berlaku

### 9.1 Apa yang ditambahkan

Seed 31 dan 2026 dijalankan untuk `concat_glu` dan `concat_fc`, di kedua protokol (8 run, 22 November 12.29–14.35, ±2 jam 6 menit, tanpa error). Data, kode, dan pengaturan sama dengan bagian 2 (T = 10, 15 epoch, `combo`, eval tiap 5). Total sekarang 5 seed per varian per protokol: 42, 7, 123, 31, 2026.

| Protokol | Fusion | Seed 31 (hash, epoch terpilih) | Seed 2026 (hash, epoch terpilih) |
|---|---|---|---|
| `within_event` | `concat_glu` | `dc45427f`, 14 | `e9ab69fe`, 9 |
| `within_event` | `concat_fc` | `adbbf987`, 14 | `9f535625`, 9 |
| `leave_event_out` | `concat_glu` | `1bdbd736`, 14 | `0722a6da`, 9 |
| `leave_event_out` | `concat_fc` | `cf1f32de`, 14 | `396575de`, 14 |

Perintah: lihat `train_seed_tambahan.out`. Rekap: `work/envs/train312/bin/python -I pipeline/rekap_seed.py work/result`. Selisih dan CI dihitung terpisah (skrip di folder kerja sementara, rumus di 9.2).

### 9.2 Cara membaca selisih

Selisih = F2 − F1, rata-rata antar seed. CI 95% memakai Welch (varians kedua kelompok boleh berbeda, derajat kebebasan sekitar 5–8). Selisih dianggap terbukti hanya bila CI tidak memuat 0. Uji permutasi (semua 252 pembagian label dari 10 nilai) dipakai sebagai pemeriksa kedua. Uji-t berpasangan per seed **tidak** dijadikan acuan, karena seed yang sama pada arsitektur berbeda tidak menghasilkan inisialisasi yang sama, jadi pasangan itu tidak benar-benar berpasangan.

### 9.3 `within_event` (n = 5)

| Ukuran | F1 `concat_glu` | F2 `concat_fc` | F2 − F1 | CI 95% | p permutasi |
|---|---|---|---|---|---|
| F1(std) | 0,763 ± 0,014 | **0,805 ± 0,031** | **+0,043** | **+0,005 s.d. +0,081** | 0,024 |
| Precision(std) | 0,655 ± 0,036 | 0,709 ± 0,047 | +0,054 | −0,008 s.d. +0,116 | 0,087 |
| Recall(std) | 0,916 ± 0,032 | 0,935 ± 0,035 | +0,019 | −0,030 s.d. +0,068 | 0,429 |
| HR@1(std) | 0,814 ± 0,024 | 0,844 ± 0,031 | +0,030 | −0,011 s.d. +0,071 | 0,151 |
| HR@3(std) | 0,874 ± 0,021 | 0,896 ± 0,031 | +0,022 | −0,018 s.d. +0,061 | 0,214 |
| NDCG@3(std) | 0,850 ± 0,022 | 0,875 ± 0,031 | +0,025 | – | – |
| FPR (turunan) | 0,618 ± 0,112 | 0,492 ± 0,113 | −0,126 | −0,290 s.d. +0,039 | – |
| HR@1 bersyarat | 0,890 ± 0,032 | 0,904 ± 0,022 | +0,014 | −0,027 s.d. +0,055 | – |

Selisih F2 − F1 per seed pada F1(std): 42 −0,004, 7 +0,079, 123 +0,079, 31 +0,006, 2026 +0,054 (F2 lebih tinggi di 4 dari 5 seed).

Pembacaan:
1. **F2 lebih baik di F1(std), tetapi tipis dan sendirian.** CI-nya hanya +0,005 di batas bawah, dan dari 5 ukuran × 2 protokol yang diuji hanya ini yang melewati batas. Dengan banyaknya perbandingan, satu hasil yang nyaris melewati batas pantas diperlakukan sebagai petunjuk, bukan temuan pasti.
2. **Sumber kenaikannya Precision (alarm palsu berkurang), bukan Recall dan bukan lokalisasi.** Precision +0,054, Recall +0,019, HR@1 bersyarat +0,014. Tetapi CI Precision sendiri sudah memuat 0.
3. **Lokalisasi setara.** HR@1(std) +0,030 dengan CI −0,011 s.d. +0,071.
4. Pada n = 3, selisih F1(std) +0,051 punya CI −0,037 s.d. +0,139 (memuat 0). Dua seed tambahan menyempitkan CI dan menggeser batas bawahnya ke atas 0, tetapi dua seed baru sendiri hanya menambah +0,006 dan +0,054.

### 9.4 `leave_event_out` (n = 5)

| Ukuran | F1 `concat_glu` | F2 `concat_fc` | F2 − F1 | CI 95% | p permutasi |
|---|---|---|---|---|---|
| F1(std) | 0,800 ± 0,047 | 0,824 ± 0,049 | +0,024 | −0,046 s.d. +0,094 | 0,437 |
| Precision(std) | 0,720 ± 0,054 | 0,763 ± 0,050 | +0,043 | −0,034 s.d. +0,119 | 0,262 |
| Recall(std) | 0,903 ± 0,071 | 0,898 ± 0,072 | −0,005 | −0,108 s.d. +0,099 | 0,905 |
| HR@1(std) | 0,582 ± 0,118 | 0,533 ± 0,073 | −0,049 | −0,197 s.d. +0,099 | 0,484 |
| HR@3(std) | 0,699 ± 0,103 | 0,638 ± 0,088 | −0,061 | −0,202 s.d. +0,080 | 0,365 |
| NDCG@3(std) | 0,650 ± 0,110 | 0,595 ± 0,082 | −0,055 | – | – |
| FPR (turunan) | 0,535 ± 0,132 | 0,425 ± 0,121 | −0,110 | −0,295 s.d. +0,075 | – |
| HR@1 bersyarat | 0,641 ± 0,090 | 0,591 ± 0,043 | −0,050 | −0,160 s.d. +0,061 | – |

Selisih F2 − F1 per seed pada HR@1(std): 42 −0,148 (seed 42 ini sama dengan angka bagian 4), 7 −0,040, 123 −0,235, **31 +0,030, 2026 +0,148**. F2 lebih tinggi di 2 dari 5 seed.

| Seed | F1 HR@1(std) | F2 HR@1(std) |
|---|---|---|
| 42 | 0,566 | 0,419 |
| 7 | 0,624 | 0,584 |
| 123 | 0,759 | 0,525 |
| 31 | 0,498 | 0,528 |
| 2026 | 0,461 | 0,609 |

Pembacaan:
1. **Klaim "F1 melokalisasi lebih baik dari F2 di event baru" runtuh.** Pada n = 3 selisihnya −0,141 (CI −0,463 s.d. +0,181, sudah memuat 0, tetapi arahnya sama di 3 seed). Dua seed tambahan memberi +0,030 dan +0,148, sehingga selisih rata-rata mengecil ke −0,049 dan arah tidak lagi konsisten.
2. **Penyebab utama: sebaran antar seed besar.** HR@1(std) F1 berkisar 0,461–0,759 (sd 0,118) hanya karena seed. Selisih rata-rata 0,05 terkubur di sebaran sebesar itu. Dengan sd ≈ 0,1 dan n = 5, selisih terkecil yang masih bisa dibedakan dari kebetulan sekitar ±0,15, sehingga selisih −0,049 memang di luar jangkauan alat ukur ini.
3. **Val tidak meramalkan Test.** Seed 123 F1 (HR@1 0,759) dan seed 2026 F1 (0,461) sama-sama dipilih di epoch 9 dengan Val combo 0,767 dan 0,742 (berdekatan), tetapi HR@1 Test-nya terpaut 0,30. Dugaan: Test `leave_event_out` berisi sedikit event, sehingga satu atau dua event yang kebetulan sulit atau mudah bagi suatu inisialisasi menggeser hasil (belum diperiksa per event).
4. **Pola alarm palsu tetap, tetapi tidak lagi terbukti.** FPR F2 lebih rendah di kedua protokol (−0,126 dan −0,110), arah sama dengan bagian 3.4 dan 4.4, tetapi CI keduanya memuat 0 pada n = 5.

### 9.5 Kesimpulan yang berlaku

| Pernyataan lama (n = 3) | Status dengan n = 5 |
|---|---|
| F2 mengurangi alarm palsu di kedua protokol | **Arahnya bertahan** (FPR −0,13 dan −0,11), tetapi CI memuat 0. Belum terbukti |
| Di `within_event`, F2 setara atau sedikit lebih baik | **F2 sedikit lebih baik di F1(std)** (+0,043, CI +0,005 s.d. +0,081); sisanya setara. Temuan tipis, perlu hati-hati |
| Di `leave_event_out`, lokalisasi F2 lebih buruk (−0,14, konsisten) | **Tidak bertahan.** Selisih −0,049, CI memuat 0, arah campuran (2 dari 5 seed F2 lebih tinggi) |
| "GLU membantu lokalisasi pada event baru" | **Tidak didukung data.** Dugaan mekanisme (gerbang meredam modalitas menyesatkan) kehilangan dasarnya |
| Penghematan parameter F2 tidak mempercepat | **Tetap berlaku** (lihat 9.7) |

Kalimat yang aman: **dengan 5 seed, F1 (dengan GLU) dan F2 (tanpa GLU) tidak bisa dibedakan secara meyakinkan di kedua protokol, kecuali kemungkinan F2 sedikit lebih baik di F1(std) `within_event`.** F2 mencapai kualitas yang kira-kira sama dengan 14% lebih sedikit parameter total (50% lebih sedikit di modul fusion). Itu hasil yang berguna sendiri: GLU tidak terbukti perlu.

Pelajaran metodologis (menggantikan yang di bagian 7): **tiga seed menghasilkan kesimpulan yang salah arah tentang lokalisasi, dan baru dua seed tambahan yang memperlihatkannya.** Selisih yang "konsisten di 3 seed" belum tentu nyata bila sebaran antar seed sebesar selisihnya. Perbandingan F3 dan F4 nanti harus memakai kelima seed ini sejak awal, dan klaim hanya dibuat bila CI-nya tidak memuat 0.

### 9.6 Keterbatasan yang tersisa

1. **n = 5 masih kecil untuk `leave_event_out`.** Selisih HR@1 terkecil yang bisa dideteksi sekitar ±0,15 (sd ≈ 0,1). Untuk mendeteksi selisih 0,05 dengan sd yang sama dibutuhkan sekitar 30 seed per varian (perkiraan kasar dari rumus CI, bukan hasil pengukuran). Itu sekitar 30 jam untuk dua varian di kedua protokol (satu run ±16 menit di T = 10), dan akan bertambah untuk F3 dan F4, jadi `leave_event_out` lebih cocok dipakai untuk melihat selisih besar saja.
2. **Seed hanya mengubah inisialisasi dan urutan batch.** Pembagian data per event tetap. Hasil ini tidak menjawab apakah kesimpulan sama bila event yang disisihkan berbeda. Itu pertanyaan generalisasi yang berbeda dari "kebetulan atau nyata antar seed".
3. **Banyak perbandingan, satu CI per perbandingan.** Tidak ada koreksi untuk perbandingan ganda. Satu-satunya CI yang melewati 0 (F1(std) `within_event`) sebaiknya dibaca sebagai petunjuk.
4. **Epoch terpilih berbeda antar run** (9 atau 14). Pemilihan lewat Val combo, jadi ikut menambah sebaran. Pembanding pada epoch tetap belum diulang untuk 5 seed.
5. **Hanya T = 10.** Fusion belum dibandingkan di T lain (lihat `Temuan_Data_dan_Sweep_T.md`, pertanyaan terbuka tentang T untuk perbandingan fusion).

### 9.7 Efisiensi dari run tambahan

| Ukuran | `within_event` F1 | `within_event` F2 | `leave_event_out` F1 | `leave_event_out` F2 |
|---|---|---|---|---|
| Detik/epoch (n = 5) | 50,7 ± 0,4 | 55,6 ± 7,0* | 57,8 ± 0,9 | 57,7 ± 1,0 |
| Inferensi (ms/jendela, n = 5) | 0,267 ± 0,004 | 0,283 ± 0,031* | 0,268 ± 0,009 | 0,266 ± 0,007 |
| Memori puncak (MB) | 2.753 ± 1 | 2.752 ± 0 | 2.788 ± 0 | 2.787 ± 1 |

\* Rata-rata ini ikut membawa seed 42 dan 7 F2 `within_event` yang dijalankan saat laptop memakai baterai (bagian 6.1), sehingga sd besar. Seed 31 dan 2026 F2 berjalan 50,0 dan 50,7 detik/epoch, sama dengan F1 (50,7 ± 0,4). Untuk `leave_event_out` ketiganya sebanding: fusion F1 dan F2 tidak berbeda dalam waktu maupun memori. Perbandingan waktu fusion yang lebih bersih ada di `Temuan_Data_dan_Sweep_T.md` bagian 17.5 (pengukuran tanpa data pada mesin yang sama).

## 10. F3: Gated Multimodal Unit (23 November, n = 5)

### 10.1 Arsitektur

F3 memakai Gated Multimodal Unit (Arevalo dkk., ICLR Workshop 2017, `literature/Gated_Multimodal_Units_for_Information_Fusion.pdf`), versi untuk lebih dari dua modalitas (Gambar 2a). Rincian implementasi dan kecocokannya dengan paper serta kode resmi penulis ada di `docs/F3_GMU.md`.

| | F1 `concat_glu` | F2 `concat_fc` | F3 `gmu` |
|---|---|---|---|
| Rumus | (Σᵢ Aᵢxᵢ) ⊙ σ(B·[x]) | ReLU(Σᵢ Aᵢxᵢ) | Σᵢ tanh(Wᵢxᵢ) ⊙ σ(W_zᵢ·[x]) |
| Gate | Satu, setelah modalitas dicampur | Tidak ada | Satu per modalitas, per dimensi, dari ketiga modalitas |
| Parameter fusion | 18.560 | 9.280 | 36.864 (2× F1) |
| Parameter total | 66.050 | 56.770 (−14%) | 84.354 (+28%) |

[x] = gabungan ketiga embedding. Gate F1 tidak bisa membedakan modalitas. Gate F3 bisa meredam satu modalitas untuk satu layanan pada satu jendela. F1 → F2 → F3 karena itu menguji dua hal: apakah gate perlu (F1 vs F2), dan apakah gate lebih baik bekerja per modalitas (F1 vs F3).

### 10.2 Hasil `within_event` (n = 5)

Selisih = F3 − pembanding, CI 95% Welch, **tebal** = CI tidak memuat 0, p = uji permutasi (252 pembagian). FPR dan HR@1 bersyarat dihitung seperti bagian 3.4 dan 4.4.

| Ukuran | F1 | F2 | F3 | F3 − F1 (CI) | p | F3 − F2 (CI) | p |
|---|---|---|---|---|---|---|---|
| F1(std) | 0,763 ± 0,014 | 0,805 ± 0,031 | 0,808 ± 0,064 | +0,045 (−0,033 s.d. +0,123) | 0,175 | +0,002 (−0,076 s.d. +0,081) | 0,960 |
| Precision(std) | 0,655 ± 0,036 | 0,709 ± 0,047 | 0,704 ± 0,091 | +0,049 (−0,063 s.d. +0,160) | 0,302 | −0,006 | 0,897 |
| Recall(std) | 0,916 ± 0,032 | 0,935 ± 0,035 | 0,955 ± 0,019 | +0,040 (−0,001 s.d. +0,080) | 0,056 | +0,021 | 0,262 |
| HR@1(std) | 0,814 ± 0,024 | 0,844 ± 0,031 | 0,856 ± 0,022 | **+0,042 (+0,008 s.d. +0,075)** | 0,024 | +0,011 (−0,029 s.d. +0,052) | 0,532 |
| HR@3(std) | 0,874 ± 0,021 | 0,896 ± 0,031 | 0,911 ± 0,023 | **+0,037 (+0,004 s.d. +0,069)** | 0,040 | +0,015 | 0,413 |
| NDCG@3(std) | 0,850 ± 0,022 | 0,875 ± 0,031 | 0,889 ± 0,022 | **+0,039 (+0,007 s.d. +0,071)** | 0,032 | +0,013 | 0,476 |
| FPR (turunan) | 0,618 ± 0,112 | 0,492 ± 0,113 | 0,534 ± 0,238 | −0,084 (−0,376 s.d. +0,208) | 0,452 | +0,042 | 0,706 |
| HR@1 bersyarat | 0,890 ± 0,032 | 0,904 ± 0,022 | 0,896 ± 0,019 | +0,006 | 0,714 | −0,008 | 0,556 |

| Seed | F3 F1(std) | F3 HR@1(std) | F3 FPR | Epoch terpilih |
|---|---|---|---|---|
| 42 | 0,864 | 0,834 | 0,33 | 9 |
| 7 | 0,869 | 0,887 | 0,34 | 9 |
| 123 | 0,729 | 0,860 | 0,87 | 9 |
| 31 | 0,754 | 0,835 | 0,69 | 9 |
| 2026 | 0,822 | 0,862 | 0,44 | 14 |

Pembacaan:
1. **Lokalisasi F3 lebih baik dari F1** (HR@1 +0,042). HR@3 dan NDCG@3 searah, tetapi ketiganya ukuran yang saling berkaitan, jadi ini satu temuan.
2. **Sumbernya Recall, bukan ketepatan lokalisasi.** HR@1 bersyarat sama (0,896 vs 0,890). F3 mendeteksi lebih banyak gangguan (Recall +0,040), dan gangguan yang terdeteksi dilokalisasi sama baiknya.
3. **Deteksi F3 tidak stabil antar seed.** Seed 123 dan 31 punya FPR 0,87 dan 0,69, sehingga sd F1(std) 0,064, terbesar di antara ketiga fusion (Levene terhadap F1: p = 0,03).
4. **Terhadap F2 tidak ada selisih.**

### 10.3 Hasil `leave_event_out` (n = 5)

| Ukuran | F1 | F2 | F3 | F3 − F1 (CI) | p | F3 − F2 (CI) | p |
|---|---|---|---|---|---|---|---|
| F1(std) | 0,800 ± 0,047 | 0,824 ± 0,049 | 0,858 ± 0,014 | **+0,059 (+0,001 s.d. +0,116)** | 0,016 | +0,035 (−0,026 s.d. +0,095) | 0,198 |
| Precision(std) | 0,720 ± 0,054 | 0,763 ± 0,050 | 0,793 ± 0,027 | **+0,073 (+0,006 s.d. +0,139)** | 0,048 | +0,030 | 0,238 |
| Recall(std) | 0,903 ± 0,071 | 0,898 ± 0,072 | 0,937 ± 0,019 | +0,034 (−0,053 s.d. +0,120) | 0,349 | +0,038 | 0,286 |
| HR@1(std) | 0,582 ± 0,118 | 0,533 ± 0,073 | 0,605 ± 0,029 | +0,023 (−0,121 s.d. +0,167) | 0,746 | +0,072 (−0,018 s.d. +0,161) | 0,056 |
| HR@3(std) | 0,699 ± 0,103 | 0,638 ± 0,088 | 0,738 ± 0,019 | +0,039 (−0,088 s.d. +0,167) | 0,405 | +0,100 (−0,008 s.d. +0,208) | 0,024 |
| NDCG@3(std) | 0,650 ± 0,110 | 0,595 ± 0,082 | 0,683 ± 0,025 | +0,033 | 0,532 | +0,089 (−0,011 s.d. +0,189) | 0,024 |
| FPR (turunan) | 0,535 ± 0,132 | 0,425 ± 0,121 | 0,371 ± 0,067 | **−0,164 (−0,326 s.d. −0,002)** | 0,063 | −0,054 | 0,484 |
| HR@1 bersyarat | 0,641 ± 0,090 | 0,591 ± 0,043 | 0,645 ± 0,028 | +0,004 | 0,929 | +0,054 (−0,001 s.d. +0,109) | 0,071 |

| Seed | F1 HR@1(std) | F2 HR@1(std) | F3 HR@1(std) | F3 F1(std) | F3 FPR | F3 epoch |
|---|---|---|---|---|---|---|
| 42 | 0,566 | 0,419 | 0,588 | 0,851 | 0,37 | 9 |
| 7 | 0,624 | 0,584 | 0,638 | 0,859 | 0,35 | 14 |
| 123 | 0,759 | 0,525 | 0,619 | 0,841 | 0,49 | 14 |
| 31 | 0,498 | 0,528 | 0,564 | 0,867 | 0,31 | 9 |
| 2026 | 0,461 | 0,609 | 0,613 | 0,875 | 0,35 | 9 |

Pembacaan:
1. **Deteksi F3 lebih baik dari F1**, karena Precision naik dan alarm palsu berkurang (FPR 0,371 vs 0,535). Buktinya tipis: batas CI +0,001 dan −0,002, dan untuk FPR uji permutasi tidak sepakat dengan CI (p = 0,063).
2. **Lokalisasi tidak berbeda** dari F1 (HR@1 +0,023, CI lebar karena sd F1 0,118). Terhadap F2, F3 lebih tinggi di HR@3 dan NDCG@3 menurut uji permutasi (p = 0,024), tetapi CI Welch memuat 0. Ini petunjuk, bukan temuan.
3. **Sebaran antar seed F3 kecil sekali**: sd HR@1 0,029 (F1 0,118, F2 0,073), sd F1(std) 0,014 (F1 0,047). Kelima seed F3 berada di 0,564–0,638, padahal F1 membentang 0,461–0,759. Tetapi uji Levene belum lolos (p = 0,09 untuk HR@1, 0,10 untuk F1(std)), dan di `within_event` polanya terbalik. Jadi "F3 lebih stabil" belum boleh diklaim.

### 10.4 Efisiensi

| Ukuran | F1 | F2 | F3 |
|---|---|---|---|
| Detik/epoch `within_event` (n = 5) | 51 | 56* | 53 |
| Detik/epoch `leave_event_out` (n = 5) | 58 | 58 | 60 |
| Inferensi (ms/jendela, dari log run) | 0,267 / 0,268 | 0,283* / 0,266 | 0,286 / 0,284 |
| Memori puncak (MB) | 2.753 / 2.788 | 2.752 / 2.787 | 2.752 / 2.787 |
| FLOPs per jendela (`ukur_efisiensi.py`) | 3,59 M | 3,09 M | 4,58 M (+28%) |

\* lihat catatan bagian 9.7. Angka "a / b" = `within_event` / `leave_event_out`.

F3 menambah 28% parameter dan FLOPs, tetapi waktu latih hanya naik 2–4% dan inferensi sekitar 6%, masih di dalam derau pengukuran (±10–20%, `Temuan_Data_dan_Sweep_T.md` bagian 17). Memori tidak berubah.

### 10.5 Kesimpulan F1 vs F2 vs F3

| Pertanyaan | Jawaban dengan n = 5 |
|---|---|
| Apakah gate perlu? (F1 vs F2) | Tidak terbukti. Satu petunjuk tipis justru menguntungkan F2 (F1(std) `within_event`) |
| Apakah gate per modalitas lebih baik dari gate setelah campur? (F3 vs F1) | Ada petunjuk ya: semua 16 selisih rata-rata searah menguntungkan F3, dua dengan CI tidak memuat 0 (tipis) |
| Apakah GMU lebih baik dari fusion tanpa gate? (F3 vs F2) | Tidak terbukti |
| Biaya | F3 +28% parameter dan FLOPs, waktu dan memori tidak beda terukur |

Kalimat yang aman: **dengan 5 seed, GMU (F3) setara atau sedikit lebih baik dari fusion asli EADRO (F1). Keunggulan yang CI-nya tidak memuat 0 hanya dua dan tipis: lokalisasi di `within_event` (berasal dari Recall yang lebih tinggi) dan deteksi di `leave_event_out` (Precision lebih tinggi, alarm palsu lebih sedikit). Terhadap F2 tidak ada selisih terbukti. Karena F3 memakai 28% parameter lebih banyak dari F1, keunggulan ini belum bisa dikaitkan khusus pada gate per modalitas.**

### 10.6 Keterbatasan F3

1. **Kapasitas tidak sama** (F3 +28% parameter terhadap F1). Pembanding dengan kapasitas setara belum dijalankan.
2. **Banyak perbandingan.** 8 ukuran × 2 skema × 2 pembanding = 32 selisih, 6 CI tidak memuat 0, tetapi keenamnya membentuk dua kelompok ukuran yang saling berkaitan. Bila semua selisih nol, sekitar 1–2 akan lolos karena kebetulan.
3. **Hiperparameter tidak disetel ulang** untuk F3 (lr, batch, epoch sama dengan F1 dan F2). Adil sebagai perbandingan, tetapi belum tentu pengaturan terbaik GMU.
4. **Nilai gate belum dianalisis.** GMU menyimpan bobot per modalitas (`last_gates`). Analisis modalitas mana yang dipakai per layanan atau per jenis gangguan belum dikerjakan.
5. Keterbatasan bagian 9.6 (n = 5 masih kecil untuk `leave_event_out`, hanya T = 10, seed tidak mengubah pembagian event) juga berlaku.

## 11. Fusion di T = 30, `within_event` (24 November, n = 5)

### 11.1 Apa yang dijalankan

Tujuan: memeriksa apakah urutan fusion di T = 10 (bagian 9–10) juga berlaku pada jendela yang lebih panjang. T = 30 dipilih sebagai T pembanding (`Ringkasan_Sweep_T_untuk_Dosen.md` bagian 4). Pengaturan sama dengan bagian 2, kecuali data `A1_T30`. Untuk `within_event`, 15 epoch dinilai cukup karena run 30 epoch memilih epoch 9 dan memberi Test yang identik (`Perbandingan_Seluruh_Eksperimen.md` bagian 5.8). `leave_event_out` T = 30 dijalankan dengan 30 epoch, hasilnya di bagian 12.

12 run baru (24 November 02.22–09.10, tanpa error, keluaran `grid_T30_15ep_we.out`). F1 seed 42, 7, dan 123 diambil dari sweep T dan dilewati otomatis oleh `run_grid.sh`.

| Fusion | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 |
|---|---|---|---|---|---|
| F1 `concat_glu` | `673f31b9`, 9 | `d746e852`, 4 | `dc8920e0`, 9 | `65d9e54d`, 9 | `19a8eea7`, 4 |
| F2 `concat_fc` | `ddfedb71`, 4 | `2673c03d`, 9 | `f25d0082`, 9 | `6b98a277`, 9 | `d1c7f1d7`, 9 |
| F3 `gmu` | `21dd8f54`, 14 | `753608fa`, 9 | `ba3e00db`, 4 | `6239cb46`, 4 | `64d50025`, 9 |

Isi sel: hash run, epoch terpilih. Perintah:

```bash
DATA_NAME=A1_T30 nohup pipeline/run_grid.sh within_event 15 "42 7 123 31 2026" "concat_glu concat_fc gmu" > grid_T30_15ep_we.out 2>&1 &
work/envs/train312/bin/python -I pipeline/banding_fusion.py 30 15 within_event
```

Cek determinisme: run F1 seed 42 dengan 30 epoch (`a3b11e96`, epoch terpilih 9) memberi Test yang sama persis dengan run 15 epoch (`673f31b9`, epoch 9). Seed yang sama memberi lintasan latih yang sama.

### 11.2 Hasil (n = 5)

Test `within_event` T = 30: 17.990 jendela gangguan dan 12.520 normal. Selisih dan CI dihitung seperti bagian 9.2. **Tebal** artinya CI tidak memuat 0.

| Ukuran | F1 | F2 | F3 | F2 − F1 (CI) | p | F3 − F1 (CI) | p | F3 − F2 (CI) | p |
|---|---|---|---|---|---|---|---|---|---|
| F1(std) | 0,829 ± 0,021 | 0,839 ± 0,022 | 0,865 ± 0,049 | +0,009 (−0,022 s.d. +0,041) | 0,508 | +0,035 (−0,025 s.d. +0,095) | 0,183 | +0,026 (−0,034 s.d. +0,086) | 0,317 |
| Precision(std) | 0,725 ± 0,034 | 0,742 ± 0,031 | 0,798 ± 0,084 | +0,017 | 0,437 | +0,073 (−0,029 s.d. +0,175) | 0,127 | +0,057 | 0,190 |
| Recall(std) | 0,970 ± 0,009 | 0,966 ± 0,020 | 0,949 ± 0,026 | −0,004 | 0,643 | −0,021 (−0,053 s.d. +0,011) | 0,127 | −0,017 | 0,262 |
| HR@1(std) | 0,833 ± 0,010 | 0,828 ± 0,016 | 0,837 ± 0,034 | −0,005 (−0,025 s.d. +0,015) | 0,603 | +0,004 (−0,038 s.d. +0,045) | 0,833 | +0,009 | 0,619 |
| HR@3(std) | 0,913 ± 0,010 | 0,906 ± 0,025 | 0,908 ± 0,034 | −0,007 | 0,595 | −0,005 | 0,897 | +0,002 | 0,952 |
| NDCG@3(std) | 0,881 ± 0,009 | 0,874 ± 0,021 | 0,880 ± 0,034 | −0,006 | 0,595 | −0,001 | 0,960 | +0,005 | 0,762 |
| FPR (turunan) | 0,532 ± 0,095 | 0,486 ± 0,078 | 0,362 ± 0,194 | −0,047 (−0,175 s.d. +0,081) | 0,444 | −0,171 (−0,409 s.d. +0,068) | 0,111 | −0,124 (−0,361 s.d. +0,113) | 0,230 |
| HR@1 bersyarat | 0,859 ± 0,012 | 0,857 ± 0,012 | 0,882 ± 0,015 | −0,002 | 0,825 | **+0,023 (+0,003 s.d. +0,043)** | 0,040 | **+0,024 (+0,005 s.d. +0,044)** | 0,032 |

Per seed:

| Seed | F1 F1(std) | F2 F1(std) | F3 F1(std) | F1 FPR | F2 FPR | F3 FPR | F1 HR@1 bersyarat | F2 HR@1 bersyarat | F3 HR@1 bersyarat |
|---|---|---|---|---|---|---|---|---|---|
| 42 | 0,847 | 0,853 | 0,887 | 0,44 | 0,48 | 0,21 | 0,871 | 0,848 | 0,858 |
| 7 | 0,851 | 0,810 | 0,909 | 0,46 | 0,60 | 0,20 | 0,841 | 0,861 | 0,896 |
| 123 | 0,834 | 0,821 | 0,889 | 0,50 | 0,52 | 0,29 | 0,869 | 0,844 | 0,890 |
| 31 | 0,811 | 0,856 | 0,854 | 0,59 | 0,45 | 0,46 | 0,854 | 0,856 | 0,886 |
| 2026 | 0,803 | 0,853 | 0,784 | 0,67 | 0,39 | 0,66 | 0,860 | 0,876 | 0,878 |

### 11.3 Efisiensi

| Ukuran | F1 | F2 | F3 |
|---|---|---|---|
| Parameter total | 68.650 | 59.370 (−13,5%) | 86.954 (+26,7%) |
| Detik/epoch (n = 5) | 125 | 125 | 127 |
| Inferensi (ms/jendela, rata-rata 5 run) | 0,889 | 0,893 | 0,916 |
| Memori puncak (MB) | 5.105 | 5.103 | 5.105 |

Parameter di T = 30 sedikit lebih banyak dari T = 10 (F1 66.050) karena sebagian lapisan bergantung pada panjang jendela. Parameter fusion sama dengan T = 10. Seperti di T = 10, tambahan parameter F3 tidak terlihat pada waktu latih maupun memori, dan inferensi hanya naik sekitar 3%, masih di dalam derau pengukuran.

### 11.4 Pembacaan

1. **F1 dan F2 tidak bisa dibedakan di T = 30.** Semua selisih F2 − F1 di bawah ±0,02. Petunjuk tipis di T = 10, yaitu F2 lebih tinggi di F1(std) (+0,043, bagian 9.3), tidak muncul lagi (+0,009). Ini menguatkan bacaan di bagian 9.5 bahwa petunjuk itu kemungkinan kebetulan.
2. **F3 cenderung lebih sedikit alarm palsu, tetapi belum terbukti.** Rata-rata FPR 0,36 vs 0,53 (F1) dan Precision +0,073. Sebarannya besar: tiga seed punya FPR 0,20–0,29, sedangkan seed 2026 0,66, setara F1 yang paling buruk. Seperti di T = 10, deteksi F3 adalah yang paling tidak stabil antar seed (sd F1(std) 0,049 vs 0,021). Levene belum lolos (p = 0,46 untuk F1(std), 0,35 untuk FPR).
3. **Satu-satunya selisih yang lolos adalah HR@1 bersyarat F3**, sekitar +0,02 terhadap F1 dan F2. Ukuran ini menilai ketepatan lokalisasi pada gangguan yang terdeteksi. F3 lebih tinggi dari F1 di 4 dari 5 seed (kecuali seed 42). Selisihnya kecil, dan dari 24 perbandingan di tabel 11.2, 1–2 bisa lolos karena kebetulan. Jadi ini petunjuk.
4. **HR@1 biasa setara** karena dua efek saling meniadakan: Recall F3 sedikit lebih rendah (−0,021), sementara HR@1 bersyaratnya lebih tinggi (+0,023).
5. **Mekanismenya berbeda dari T = 10.** Di T = 10, HR@1 F3 lebih tinggi karena Recall lebih tinggi, sementara HR@1 bersyaratnya sama (bagian 10.2). Di T = 30 kebalikannya. Yang konsisten di kedua T hanyalah **arah**: tidak ada ukuran di mana F3 lebih buruk dari F1 secara berarti. Jalur keunggulannya tidak konsisten, jadi belum ada penjelasan mekanistis yang bisa dipegang.

### 11.5 Perbandingan dengan T = 10 (`within_event`)

| Selisih (CI 95% Welch) | T = 10 F1(std) | T = 30 F1(std) | T = 10 HR@1(std) | T = 30 HR@1(std) | T = 10 HR@1 bersyarat | T = 30 HR@1 bersyarat |
|---|---|---|---|---|---|---|
| F2 − F1 | **+0,043** | +0,009 | +0,030 | −0,005 | +0,014 | −0,002 |
| F3 − F1 | +0,045 | +0,035 | **+0,042** | +0,004 | +0,006 | **+0,023** |
| F3 − F2 | +0,002 | +0,026 | +0,011 | +0,009 | −0,008 | **+0,024** |

- Di T = 30, selisih antar fusion **lebih kecil** dari selisih antar T. Ketiga fusion naik F1(std) +0,07 s.d. +0,10 dari T = 10 F1 (CI tidak memuat 0, `Perbandingan_Seluruh_Eksperimen.md` bagian 3.1), sedangkan selisih fusion terbesar di T = 30 adalah +0,035. Untuk deteksi, panjang jendela lebih berpengaruh daripada pilihan fusion.
- Untuk HR@1(std), T = 30 mempersempit selisih antar fusion: di T = 10 rentangnya 0,814–0,856, di T = 30 hanya 0,828–0,837. Dengan jendela panjang, ketiga fusion melokalisasi hampir sama baiknya.
- Dua tanda tebal di T = 10 (F2 − F1 F1(std), F3 − F1 HR@1) tidak berulang di T = 30, dan tanda tebal di T = 30 (HR@1 bersyarat) tidak ada di T = 10. Tidak ada satu pun selisih fusion yang lolos di kedua T. Ini konsisten dengan dugaan bahwa selisih fusion yang lolos sejauh ini sebagian besar adalah derau dari banyaknya perbandingan.

### 11.6 Kesimpulan sementara (T = 30 `within_event` saja)

Kalimat yang aman: **di T = 30 `within_event`, F1, F2, dan F3 setara untuk deteksi dan lokalisasi. F3 cenderung lebih sedikit alarm palsu (tidak terbukti, sangat bergantung seed) dan sedikit lebih tepat melokalisasi gangguan yang terdeteksi (HR@1 bersyarat +0,02, tipis). Keunggulan F3 atas F1 di T = 10 tidak berulang dalam bentuk yang sama.** Hasil `leave_event_out` T = 30 ada di bagian 12, dan kesimpulan T = 30 secara utuh di bagian 12.6.

Keterbatasan bagian 10.6 tetap berlaku. Tambahannya: Test `within_event` T = 30 berbeda dari Test T = 10 (jumlah dan komposisi jendela), sehingga tabel 11.5 membandingkan pola, bukan angka absolut.

## 12. Fusion di T = 30, `leave_event_out` (25 November, n = 5)

### 12.1 Apa yang dijalankan

Pengaturan sama dengan bagian 11, kecuali skema `leave_event_out` dan **30 epoch**. Alasannya ada di `Perbandingan_Seluruh_Eksperimen.md` bagian 5.8: di skema ini Val masih naik sampai epoch 29. Ketiga fusion memakai 30 epoch, jadi perbandingan antar fusion tetap adil. Perbandingan dengan T = 10 (15 epoch) tidak setara (bagian 12.5).

14 run baru (24 November 14.03 sampai 25 November 07.45, tanpa error, keluaran `grid_T30_30ep_leo.out`). F1 seed 42 diambil dari run cek epoch (`14f5c50b`) dan dilewati otomatis oleh `run_grid.sh`.

| Fusion | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 |
|---|---|---|---|---|---|
| F1 `concat_glu` | `14f5c50b`, 29 | `976904d0`, 14 | `6eb3da64`, 29 | `82bb4aff`, 24 | `1ac664fe`, 9 |
| F2 `concat_fc` | `e1573c26`, 29 | `96f409f0`, 9 | `00500951`, 24 | `ab9e6771`, 24 | `27d97dfc`, 29 |
| F3 `gmu` | `089479dd`, 29 | `e58b4816`, 29 | `6d0986d0`, 24 | `9550e53b`, 29 | `b2b1a70e`, 19 |

Isi sel: hash run, epoch terpilih. Perintah:

```bash
DATA_NAME=A1_T30 nohup pipeline/run_grid.sh leave_event_out 30 "42 7 123 31 2026" "concat_glu concat_fc gmu" > grid_T30_30ep_leo.out 2>&1 &
work/envs/train312/bin/python -I pipeline/banding_fusion.py 30 30 leave_event_out
```

### 12.2 Hasil (n = 5)

Test `leave_event_out` T = 30: 16.932 jendela gangguan dan 9.880 normal. Selisih dan CI dihitung seperti bagian 9.2. **Tebal** artinya CI tidak memuat 0. Dengan 5 lawan 5 nilai, p terkecil yang mungkin pada uji permutasi adalah 2/252 = 0,008. Nilai itu berarti kelima nilai satu kelompok semuanya di atas (atau di bawah) kelima nilai kelompok lain.

| Ukuran | F1 | F2 | F3 | F2 − F1 (CI) | p | F3 − F1 (CI) | p | F3 − F2 (CI) | p |
|---|---|---|---|---|---|---|---|---|---|
| F1(std) | 0,849 ± 0,039 | 0,850 ± 0,041 | 0,910 ± 0,020 | +0,001 (−0,058 s.d. +0,059) | 0,960 | **+0,061 (+0,013 s.d. +0,109)** | 0,016 | **+0,060 (+0,010 s.d. +0,110)** | 0,024 |
| Precision(std) | 0,784 ± 0,033 | 0,772 ± 0,059 | 0,872 ± 0,024 | −0,012 | 0,738 | **+0,089 (+0,046 s.d. +0,131)** | 0,008 | **+0,101 (+0,028 s.d. +0,173)** | 0,008 |
| Recall(std) | 0,928 ± 0,052 | 0,949 ± 0,041 | 0,952 ± 0,026 | +0,022 | 0,492 | +0,024 (−0,040 s.d. +0,089) | 0,429 | +0,003 | 0,905 |
| HR@1(std) | 0,560 ± 0,064 | 0,591 ± 0,081 | 0,599 ± 0,063 | +0,031 (−0,076 s.d. +0,138) | 0,508 | +0,039 (−0,054 s.d. +0,131) | 0,365 | +0,008 (−0,099 s.d. +0,114) | 0,849 |
| HR@3(std) | 0,651 ± 0,034 | 0,722 ± 0,083 | 0,750 ± 0,058 | +0,070 (−0,031 s.d. +0,172) | 0,135 | **+0,099 (+0,026 s.d. +0,171)** | 0,008 | +0,028 | 0,540 |
| NDCG@3(std) | 0,614 ± 0,046 | 0,669 ± 0,081 | 0,687 ± 0,060 | +0,055 | 0,238 | +0,072 (−0,006 s.d. +0,151) | 0,079 | +0,017 | 0,706 |
| FPR (turunan) | 0,439 ± 0,068 | 0,492 ± 0,171 | 0,240 ± 0,050 | +0,053 (−0,155 s.d. +0,262) | 0,619 | **−0,199 (−0,287 s.d. −0,111)** | 0,008 | **−0,252 (−0,461 s.d. −0,043)** | 0,008 |
| HR@1 bersyarat | 0,603 ± 0,052 | 0,624 ± 0,091 | 0,629 ± 0,062 | +0,021 | 0,683 | +0,026 (−0,059 s.d. +0,110) | 0,500 | +0,005 | 0,921 |

Per seed:

| Seed | F1 F1(std) | F2 F1(std) | F3 F1(std) | F1 FPR | F2 FPR | F3 FPR | F1 HR@1 | F2 HR@1 | F3 HR@1 | F1 HR@1 bersyarat | F2 HR@1 bersyarat | F3 HR@1 bersyarat |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 42 | 0,787 | 0,851 | 0,903 | 0,51 | 0,34 | 0,20 | 0,507 | 0,646 | 0,591 | 0,604 | 0,729 | 0,645 |
| 7 | 0,851 | 0,860 | 0,879 | 0,42 | 0,49 | 0,33 | 0,478 | 0,487 | 0,587 | 0,518 | 0,502 | 0,630 |
| 123 | 0,872 | 0,789 | 0,921 | 0,39 | 0,76 | 0,21 | 0,609 | 0,556 | 0,545 | 0,641 | 0,590 | 0,568 |
| 31 | 0,847 | 0,903 | 0,923 | 0,51 | 0,36 | 0,23 | 0,622 | 0,695 | 0,565 | 0,652 | 0,699 | 0,579 |
| 2026 | 0,890 | 0,848 | 0,925 | 0,36 | 0,51 | 0,23 | 0,586 | 0,574 | 0,707 | 0,603 | 0,601 | 0,724 |

### 12.3 Efisiensi

| Ukuran | F1 | F2 | F3 |
|---|---|---|---|
| Parameter total | 68.650 | 59.370 (−13,5%) | 86.954 (+26,7%) |
| Detik/epoch (n = 5) | 158 (144 tanpa seed 42) | 143 | 145 |
| Waktu per run (30 epoch) | ±75 menit | ±75 menit | ±76 menit |
| Inferensi (ms/jendela) | 0,877 (4 run, tanpa seed 42) | 0,879 | 0,897 |
| Memori puncak (MB) | 5.314 | 5.314 | 5.315 |

F1 seed 42 berasal dari run cek epoch yang berjalan sekitar 50% lebih lambat (215 s/epoch, inferensi 1,41 ms), kemungkinan karena mode daya laptop (`Perbandingan_Seluruh_Eksperimen.md` bagian 5.8). Kalau run itu dikeluarkan, ketiga fusion sama cepatnya. Tambahan parameter F3 (+27%) hanya menambah sekitar 2% pada inferensi, sama seperti di T = 10 dan T = 30 `within_event`.

### 12.4 Pembacaan

1. **F3 lebih baik dari F1 dan F2 untuk deteksi, dan kali ini jelas.** F1(std) F3 lebih tinggi dari F1 dan dari F2 di kelima seed, dan CI kedua selisih tidak memuat 0. Di T = 10 dan di T = 30 `within_event`, F3 belum pernah terbukti lebih baik dari F2 pada ukuran utama.
2. **Sumbernya alarm palsu, bukan gangguan yang terlewat.** Recall ketiga fusion hampir sama (0,93–0,95). Yang berbeda adalah Precision (+0,09 sampai +0,10) dan FPR. FPR tertinggi F3 (0,33, seed 7) masih di bawah FPR terendah F1 (0,36, seed 2026). Artinya, pada event yang belum pernah dilihat, F3 jauh lebih jarang menandai jendela normal sebagai gangguan. Polanya sama dengan T = 10 `leave_event_out` (Precision +0,073, FPR −0,164, bagian 10.3), tetapi sekarang lebih besar dan juga berlaku terhadap F2.
3. **Lokalisasi tidak berbeda.** HR@1(std) dan HR@1 bersyarat ketiga fusion tidak bisa dibedakan, dan sebaran antar seed (sd 0,06–0,09) lebih besar dari selisihnya (≤0,04). HR@3 F3 lebih tinggi dari F1 (+0,099, p = 0,008), tetapi tidak dari F2 (+0,028). F2 juga lebih tinggi dari F1 di HR@3 (+0,070, belum terbukti). Jadi yang terlihat mungkin F1 yang lemah di HR@3 pada kondisi ini (sd F1 hanya 0,034), bukan keunggulan khas F3. Ini dibaca sebagai petunjuk.
4. **F2 setara F1 di semua ukuran** (semua p ≥ 0,13). Ini sama dengan T = 10 dan T = 30 `within_event`. Membuang GLU tidak mengubah hasil.
5. **F3 tampak lebih stabil, tetapi belum terbukti.** sd F1(std) F3 0,020 vs 0,039 (F1) dan 0,041 (F2), dan sd FPR 0,050 vs 0,068 dan 0,171. Levene belum lolos (p = 0,41 terhadap F1, 0,47 terhadap F2 untuk F1(std)). Pola yang sama terlihat di T = 10 `leave_event_out` (sd 0,014 vs 0,047).
6. **Soal banyaknya perbandingan.** 7 dari 24 selisih di tabel 12.2 lolos. Bila semuanya nol sebenarnya, yang lolos karena kebetulan kira-kira 1–2. Jadi 7 jauh di atas itu. Tetapi F1(std), Precision, dan FPR mengukur gejala yang sama (alarm palsu), sehingga ketujuhnya lebih tepat dihitung sebagai **satu temuan kuat** (F3 mengurangi alarm palsu, terhadap F1 dan F2) **ditambah satu petunjuk** (HR@3 terhadap F1).

### 12.5 Perbandingan dengan T = 10 (`leave_event_out`)

| Selisih (CI 95% Welch) | T = 10 F1(std) | T = 30 F1(std) | T = 10 FPR | T = 30 FPR | T = 10 HR@1(std) | T = 30 HR@1(std) | T = 10 HR@1 bersyarat | T = 30 HR@1 bersyarat |
|---|---|---|---|---|---|---|---|---|
| F2 − F1 | +0,024 | +0,001 | −0,110 | +0,053 | −0,049 | +0,031 | −0,050 | +0,021 |
| F3 − F1 | **+0,059** | **+0,061** | **−0,164** | **−0,199** | +0,023 | +0,039 | +0,004 | +0,026 |
| F3 − F2 | +0,035 | **+0,060** | −0,054 | **−0,252** | +0,072 | +0,008 | +0,054 | +0,005 |

- **F3 − F1 di F1(std) dan FPR lolos di kedua T, dengan besar yang hampir sama** (+0,06; −0,16 dan −0,20). Ini selisih fusion pertama yang berulang lintas T. Pernyataan di bagian 11.5 ("tidak ada selisih fusion yang lolos di kedua T") sekarang hanya berlaku untuk `within_event`.
- F3 − F2 baru lolos di T = 30. Di T = 10 arahnya sama tetapi belum terbukti, karena F2 di T = 10 sendiri sudah sedikit lebih rendah FPR-nya dari F1 (−0,110). Di T = 30, F2 tidak lagi lebih baik dari F1.
- Lokalisasi tidak membaik di kedua T, untuk fusion mana pun.
- Angka absolut antar T **tidak setara**: epoch berbeda (15 vs 30) dan Test berbeda. Sebagai gambaran saja, HR@1(std) T = 30 tidak lebih tinggi dari T = 10 (F1 0,560 vs 0,582; F3 0,599 vs 0,605), sedangkan F1(std) lebih tinggi (F3 0,910 vs 0,858).
- Di `within_event` T = 30, arah FPR sama (F3 0,36 vs F1 0,53), tetapi tidak terbukti karena sebaran seed F3 besar (0,20–0,66, bagian 11.4). Jadi pengurangan alarm palsu oleh F3 **terbukti di skema event baru dan searah di skema event yang sama**.

### 12.6 Kesimpulan T = 30 (kedua skema) dan dampaknya pada pertanyaan penelitian

Kalimat yang aman:

- **Di `leave_event_out`, F3 (GMU) mendeteksi gangguan lebih baik dari F1 dan F2. Penyebabnya alarm palsu yang jauh lebih sedikit (FPR T = 30: 0,24 vs 0,44 dan 0,49, di kelima seed). Terhadap F1, pengurangan ini muncul di T = 10 dan T = 30 dengan besar yang hampir sama.**
- **Lokalisasi (HR@1) tidak berbeda antar fusion, di T dan skema mana pun.**
- **F2 setara F1 di semua kondisi yang diuji (2 T × 2 skema).**
- Di `within_event`, ketiga fusion setara. Keunggulan F3 hanya tampak sebagai arah (FPR lebih rendah, HR@1 bersyarat +0,02).

Dampak pada dua pertanyaan F1 → F2 → F3:

1. **Apakah gate diperlukan?** Tidak terlihat. Membuang GLU (F2) tidak mengubah deteksi maupun lokalisasi.
2. **Di mana gate diletakkan?** Gate per modalitas (F3) membantu **deteksi pada event baru**, lewat alarm palsu yang lebih sedikit. Gate per modalitas tidak membantu lokalisasi.

Penjelasan yang masuk akal: gate per modalitas memungkinkan model mengecilkan modalitas yang "ramai" pada jendela normal sebelum digabung, sehingga skor anomali tidak ikut naik. Ini **dugaan**. Nilai gate (`last_gates`) belum dianalisis, jadi belum diketahui modalitas mana yang dikecilkan.

### 12.7 Keterbatasan

1. **Mungkin belum konvergen.** Epoch 29 (evaluasi terakhir) terpilih di 3 dari 5 run F3, 2 run F1, dan 2 run F2. Val masih naik, jadi angka bisa bergeser dengan epoch lebih banyak. Test hanya tercatat pada epoch yang Val-nya menjadi rekor baru, sehingga perbandingan pada epoch tetap tidak bisa dihitung ulang dari log. Seperti di bagian 9.4, Val `leave_event_out` juga tidak meramalkan Test dengan baik, jadi epoch yang terpilih pun sebagian acak.
2. **Kapasitas bercampur dengan arsitektur.** F3 punya 27% parameter lebih banyak dari F1. F2 (14% lebih sedikit) setara F1, jadi berkurangnya kapasitas tidak merugikan. Namun belum diuji apakah F1 yang diperbesar sampai kapasitas F3 juga mengurangi alarm palsu. Tanpa uji itu, keunggulan F3 belum bisa dikaitkan khusus pada gate per modalitas.
3. **Tidak setara dengan T = 10** (30 vs 15 epoch, Test berbeda). Tabel 12.5 membandingkan pola selisih, bukan angka absolut.
4. **Satu pembagian event.** Seed hanya mengubah inisialisasi dan urutan batch. Hasil ini belum tentu berlaku untuk pilihan event Test yang lain.
5. Keterbatasan bagian 10.6 (nilai gate belum dianalisis, tidak ada analisis per jenis gangguan) tetap berlaku.

---

## Lampiran. Berkas terkait

| Berkas | Isi |
|---|---|
| `work/result/<hash>/running.log` | Log tiap run (metrik Val/Test per epoch, baris `Efficiency`) |
| `train_F2_within.out`, `train_F2_leo.out` | Keluaran grid F2 |
| `pipeline/rekap_seed.py` | Rekap otomatis dan tabel perbandingan fusion |
| `work/chunks/A1/<protokol>/split_summary.json` | Jumlah jendela per split dan kelas |
| `Report/Laporan_Eksperimen_Seed.md` | Baseline F1 `within_event` dan `leave_event_out` |
| `Report/Laporan_Efisiensi_F1.md` | Efisiensi baseline F1 |
| `Eadro/codes/model.py` | Implementasi `ConcatFC`, `GatedMultimodalUnit` (F3), dan fusion lain |
| `docs/F3_GMU.md` | Dokumentasi F3: rumus, kecocokan dengan paper dan kode resmi, efisiensi, hasil lengkap |
| `pipeline/banding_fusion.py` | Rekap F1/F2/F3 (FPR, HR@1 bersyarat, CI Welch, uji permutasi) |
| `grid_gmu.out` | Keluaran grid F3 |
| `grid_T30_15ep_we.out` | Keluaran grid F1/F2/F3 T = 30 `within_event` (bagian 11) |
| `grid_T30_30ep_leo.out` | Keluaran grid F1/F2/F3 T = 30 `leave_event_out`, 30 epoch (bagian 12) |
| `Eadro/codes/base.py` | Fungsi `evaluate()`, termasuk definisi metrik (std) |
