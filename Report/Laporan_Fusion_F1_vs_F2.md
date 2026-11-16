# Laporan Perbandingan Fusion: F1 (`concat_glu`) vs F2 (`concat_fc`)

| | |
|---|---|
| Tanggal | 16 November 2026 |
| Data | Train Ticket (TT), `A1`, jendela T = 10 detik |
| Protokol | `within_event` dan `leave_event_out` |
| Pengaturan | 15 epoch, batch 256, lr 0,001, epoch dipilih dengan `combo` = (F1(std) + HR@1(std))/2 di Val, evaluasi tiap 5 epoch |
| Seed | 42, 7, 123 |
| Perbedaan antar varian | Hanya modul fusion. Data, kode, environment, dan hyperparameter lain identik (dicek lewat `params.json` dan tanggal berkas) |
| Perintah F2 | `pipeline/run_grid.sh within_event 15 "42 7 123" "concat_fc"` dan `pipeline/run_grid.sh leave_event_out 15 "42 7 123" "concat_fc"` |
| Rekap | `work/envs/train312/bin/python pipeline/rekap_seed.py work/result` |

Angka F1 berasal dari run baseline yang sama di `Laporan_Eksperimen_Seed.md` dan `Laporan_Efisiensi_F1.md`.

**Ringkasan:** Di `within_event` (event yang sudah pernah dilihat), F2 setara atau sedikit lebih baik dari F1. Di `leave_event_out` (event baru), F2 tetap mengurangi alarm palsu, tetapi **lokalisasinya jelas lebih buruk** (HR@1(std) −0,14, konsisten di ketiga seed). GLU tidak berpengaruh pada event yang dikenal, tetapi membantu lokalisasi pada event baru.

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

## 7. Kesimpulan

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

1. **Jumlah seed kecil (n = 3).** Untuk memperkuat klaim lokalisasi di `leave_event_out`, seed tambahan (misalnya total 5 per varian) sebaiknya ditambahkan untuk semua varian fusion sekaligus setelah F3 dan F4 selesai.
2. **Angka waktu F2 `within_event` sebagian diukur saat memakai baterai.** Angka final diambil dari skrip benchmark `model.ckpt` yang mengukur semua varian dalam satu sesi (rencana di `Laporan_Efisiensi_F1.md` bagian 6).
3. **`random_original` belum dijalankan untuk F2.** Protokol ini bocor dan baseline-nya hampir mentok, sehingga kurang informatif untuk membandingkan fusion. Rencananya dijalankan di akhir untuk semua varian.
4. **Analisis per jenis gangguan dan per layanan belum dilakukan.** Log hanya menyimpan metrik agregat. Analisis ini memerlukan skrip yang memuat `model.ckpt` dan menyimpan prediksi per jendela, misalnya untuk melihat apakah penurunan lokalisasi F2 terpusat di jenis gangguan tertentu.
5. **F3 dan F4 belum dijalankan.** F3 (Learnable Weighted Feature Fusion: MULAN, Topo-MFP) dan F4 (Cross-Attention: FAMOS) menunggu PDF paper rujukan.

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
| `Eadro/codes/model.py` | Implementasi `ConcatFC` dan fusion lain |
| `Eadro/codes/base.py` | Fungsi `evaluate()`, termasuk definisi metrik (std) |
