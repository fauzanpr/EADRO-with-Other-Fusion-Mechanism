# Ringkasan Sweep Panjang Jendela (T) pada Dataset Train Ticket

| | |
|---|---|
| Tanggal | 22 November 2026 |
| Untuk | Pak Fitra |
| Cakupan | Dataset Train Ticket (TT), model EADRO dengan fusion `concat_glu` |
| Rincian lengkap | `Report/Temuan_Data_dan_Sweep_T.md` (bagian 10–16) |

## 1. Yang diminta dan yang dikerjakan

Saran Bapak (10 November): jalankan 3 seed, dan coba T yang lebih kecil dan lebih besar dari T = 10. Sudah dikerjakan **T = 5, 10, 30, 40, 50, 60, masing-masing 3 seed (42, 7, 123)**. T = 5 hanya di skema `within_event`; T lain di kedua skema.

- `within_event`: event gangguan yang sama muncul di data latih dan uji (pembagian menurut waktu).
- `leave_event_out`: event di data uji belum pernah dilihat saat latih. Ini skema yang lebih ketat untuk lokalisasi.
- Pengaturan lain tetap: 15 epoch, learning rate 0,001, batch 256, jendela digeser tiap 1 detik (tanpa stride) untuk semua T, sehingga sebanding. Metrik yang dilaporkan adalah versi `(std)` pada kelas gangguan, di data Test, pada epoch yang dipilih lewat Val.
- Jumlah parameter model naik 130 per detik T (65.400 pada T = 5 sampai 72.550 pada T = 60). Itu terverifikasi dari kode dan dari keenam run.

## 2. Perbandingan tiap T

Rata-rata 3 seed. Nilai terbaik per kolom dicetak tebal.

### `within_event`

| T | F1 | Recall | Precision | HR@1 | HR@3 | Alarm palsu* |
|---|---|---|---|---|---|---|
| 5 | 0,743 | 0,942 | 0,616 | 0,799 | 0,878 | 0,74 |
| 10 | 0,767 | 0,923 | 0,658 | 0,822 | 0,883 | 0,62 |
| 30 | 0,844 | 0,968 | 0,749 | 0,832 | 0,915 | 0,47 |
| 40 | 0,823 | 0,940 | 0,732 | 0,824 | 0,894 | 0,53 |
| 50 | 0,854 | 0,970 | 0,765 | **0,850** | 0,922 | 0,51 |
| 60 | **0,892** | **0,992** | **0,814** | 0,842 | **0,933** | **0,42** |

### `leave_event_out`

| T | F1 | Recall | Precision | HR@1 | HR@3 | Alarm palsu* |
|---|---|---|---|---|---|---|
| 10 | 0,806 | 0,938 | 0,706 | **0,650** | **0,754** | 0,59 |
| 30 | 0,837 | 0,922 | 0,766 | 0,517 | 0,622 | 0,48 |
| 40 | 0,877 | 0,962 | 0,806 | 0,576 | 0,695 | 0,43 |
| 50 | **0,905** | 0,983 | **0,839** | 0,539 | 0,652 | **0,38** |
| 60 | 0,896 | **0,992** | 0,819 | 0,529 | 0,680 | 0,47 |

\* Alarm palsu = bagian jendela normal yang salah dinyatakan gangguan (turunan dari Precision dan Recall, bukan dicatat langsung oleh kode). Makin kecil makin baik.

Sebaran antar seed (sd) cukup besar: F1 0,01–0,06 dan HR@1 0,01–0,10. Angka lengkap dengan sd ada di laporan rinci.

### Biaya komputasi (laptop CPU i7-8650U, 15 GB RAM, tanpa GPU)

| T | Detik per epoch (`within`) | Waktu 3 seed (`within`) | Inferensi, batch 256 (ms per jendela) | RAM puncak proses latih (`within` / `leave`) | Membangun data |
|---|---|---|---|---|---|
| 5 | 32 | ±30 menit | 0,18 ms | 2,1 GB / – | – |
| 10 | 51 | ±45 menit | 0,27 ms | 2,8 GB / 2,8 GB | ±47 menit |
| 30 | 124 | ±1 jam 40 menit | 0,88 ms | 5,1 GB / 5,3 GB | 1 jam 57 menit |
| 40 | 168 | 2 jam 16 menit | 1,47 ms | 6,1 GB / 6,5 GB | 2 jam 27 menit |
| 50 | 214 | 2 jam 54 menit | 2,10 ms | 7,1 GB / 7,6 GB | 2 jam 56 menit |
| 60 | 260 | 3 jam 33 menit | 2,79 ms | 8,0 GB / 8,8 GB | 3 jam 29 menit |

`leave_event_out` ±15–19% lebih lama per epoch (T = 60: 310 detik, 4 jam 8 menit untuk 3 seed). Dibanding T = 10, T = 60 memakan ±5× waktu latih per epoch (5,7× per jendela latih). Angka inferensi di atas adalah throughput batch (untuk evaluasi offline), dan RAM puncak adalah biaya pipeline latih di laptop ini (seluruh dataset di memori), bukan memori model. Ukuran yang lebih tepat untuk efisiensi ada di bagian 2.1.

Grafik: `Report/Gambar_Kurva_T.png` (F1 dan HR@1 terhadap T) dan `Report/Gambar_Biaya_T.png` (biaya terhadap T).

### 2.1 Efisiensi: biaya per ukuran, dan kualitas melawan biaya

Tabel biaya di atas belum cukup sebagai ukuran efisiensi (hanya biaya, dan beberapa kolom mengukur pipeline latih, bukan model). Karena itu ditambah pengukuran tanpa data nyata (data acak berbentuk sama, median 3 ronde, laptop yang sama; derau antar ronde ±10–20%, jadi hanya selisih yang lebih besar dari itu yang berarti). Skrip: `pipeline/ukur_efisiensi.py`; rincian di `Report/Temuan_Data_dan_Sweep_T.md` bagian 17.

| T | FLOPs per jendela (juta) | Latensi satu jendela (ms) | Inferensi batch 256 (ms per jendela) | Latih per jendela (ms, sintetis) | Latensi deteksi |
|---|---|---|---|---|---|
| 5 | 3,24 | 1,95 | 0,18 | 0,81 | 5 detik |
| 10 | 3,59 | 1,86 | 0,26 | 1,46 | 10 detik |
| 30 | 4,97 | 2,39 | 1,06 | 4,24 | 30 detik |
| 40 | 5,66 | 2,52 | 1,55 | 5,64 | 40 detik |
| 50 | 6,35 | 2,69 | 2,01 | 7,09 | 50 detik |
| 60 | 7,04 | 2,89 | 2,63 | 8,72 | 60 detik |
| **60 / 10** | **2,0×** | **1,55×** | **10×** | **6,0×** | **6×** |

- **FLOPs bukan proxy yang baik untuk biaya T di model ini:** FLOPs hanya naik 2×, tetapi waktu latih 6× dan inferensi batch 10×. Dugaan (belum diuji dengan profiler): waktu dibatasi memori pada tensor aktivasi yang tumbuh dengan T.
- **Inferensi satu jendela tidak menjadi hambatan di T mana pun:** 1,9–2,9 ms, kurang dari 0,5% dari 1 detik antar jendela (stride 1). Yang membedakan T secara operasional adalah **latensi deteksi**: model baru bisa memutuskan setelah T detik data terkumpul.
- **Kualitas melawan biaya** (`Report/Gambar_Efisiensi_T.png`): di `within_event` hanya langkah T = 10 → 30 yang memberi kenaikan signifikan (F1 +0,077) dengan biaya latih ×2,5. Dari T = 30 ke 60 biaya naik ×2,2 lagi untuk F1 +0,048 dan HR@1 +0,010 (di dalam sd). Di `leave_event_out` tidak ada T yang mengalahkan T = 10 pada HR@1, sementara biaya naik ×2,4 sampai ×5,5.
- **Varian fusion** (T = 10, lima varian yang ada di kode; F3 dan F4 belum diimplementasi): parameter dan FLOPs berbeda (−14% untuk `concat_fc`, `sum`, `attn`; +29% untuk `lmf`, dibanding `concat_glu`), tetapi **waktu tidak berbeda terukur** (selisih di bawah derau). Biaya akibat T (6–10×) jauh melampaui biaya akibat pilihan fusion, jadi efisiensi bukan penentu pemilihan fusion; kualitas yang menentukan.

## 3. Temuan

1. **Deteksi (F1, Recall, alarm palsu) cenderung membaik saat T naik.** Di `within_event` F1 naik dari 0,743 (T = 5) ke 0,892 (T = 60) dan alarm palsu turun dari 0,74 ke 0,42; kenaikannya tidak monoton (T = 40 di bawah T = 30). Di `leave_event_out` F1 naik dari 0,806 (T = 10) ke 0,905 (T = 50), lalu mendatar di T = 60 (0,896).
2. **Lokalisasi (HR@1) tidak membaik dengan T.**
   - Di `within_event` HR@1 hampir tetap di 0,80–0,85 pada semua T.
   - Di `leave_event_out` HR@1 tertinggi justru di T = 10 (0,650) dan di T ≥ 30 turun ke 0,52–0,58.
   - HR@1 di antara fault yang terdeteksi di `leave_event_out` juga turun (0,690 pada T = 10, 0,534 pada T = 60). Jadi turunnya bukan karena fault terlewat; biangnya memang kurang sering di urutan pertama.
3. **Kedua skema sangat berbeda untuk lokalisasi.** Pada T = 60, F1 hampir sama (0,892 vs 0,896), tetapi HR@1 0,842 vs 0,529. Celah ±0,31 itu tidak menyempit saat T naik. Menentukan biang untuk event yang belum pernah dilihat adalah bagian yang sulit.
4. **Signifikansi: hampir semua selisih terhadap T = 10 belum bisa dibedakan dari derau.** Dengan 3 seed, selang kepercayaan 95% (Welch, t = 4,303) untuk selisih mencakup nol pada hampir semua perbandingan. Satu-satunya yang melewati batas adalah **F1 T = 30 vs T = 10 di `within_event`** (+0,077; SK +0,031 s.d. +0,123). Yang bisa dinyatakan untuk sisanya hanyalah arah rata-rata ("cenderung"), bukan "terbukti".
5. **Biaya naik tajam, hasil tidak sebanding.** T = 30 memberi lompatan terbesar di `within_event` dengan biaya sedang (±2,5× waktu latih per jendela). Di atas T = 30 biaya terus naik (T = 60: ±5,7×) dengan keuntungan deteksi yang kecil dan tidak signifikan, dan tanpa keuntungan lokalisasi. Latensi deteksi juga naik 6× (10 → 60 detik), sedangkan inferensi satu jendela tetap di bawah 3 ms (bagian 2.1).
6. **Hipotesis trace tidak terbukti.** Data trace datang dalam lonjakan 1 detik tiap ±60 detik, sehingga hanya T = 60 yang hampir semua jendelanya (±95%) memuat trace (T = 10: ±18%). Pada T = 60 deteksi memang tertinggi di `within_event`, tetapi lokalisasi tidak membaik di kedua skema. Jendela yang lebih panjang juga memberi metrik dan log yang lebih panjang, jadi kenaikan deteksi belum bisa dikaitkan ke trace. Pengujian yang tepat adalah ablasi modalitas, belum dilakukan.

## 4. Keterbatasan

- **Hanya 3 seed.** Dengan sd HR@1 0,05–0,10, selisih di bawah ±0,2 tidak bisa dibedakan dari derau. 5 seed atau lebih akan memperjelas temuan 1 dan 2.
- **Data Test tidak identik antar T.** Jendela yang makin panjang membuat jumlah jendela uji, jendela yang dibuang di batas pembagian, dan porsi normal berubah (porsi normal di Test `within_event`: 44% pada T = 10 menjadi 36% pada T = 60). Sebagian selisih antar T bisa berasal dari komposisi data, bukan dari T.
- **15 epoch kemungkinan kurang untuk T besar.** Epoch 14 (evaluasi terakhir) dipilih pada ketiga seed di `within_event` T = 50 dan 60, dan pada 8 dari 12 run `leave_event_out` T ≥ 30. Belum diuji apakah epoch lebih panjang mengubah kesimpulan.
- **Val kecil di T besar** (T = 60 `within_event`: hanya 1.034 jendela gangguan), dan di `leave_event_out` Val tidak mewakili Test (HR@1 Val ±0,8 vs Test ±0,5).
- **Hanya `concat_glu`.** Apakah pola ini sama untuk fusion lain belum diketahui; itu justru tujuan utama proyek.
- Seluruh angka waktu dan RAM berasal dari satu laptop CPU dan tidak boleh dibandingkan dengan hardware lain. Ukuran efisiensi di bagian 2.1 memakai data acak berbentuk sama (nilai absolut sintetis 15–30% di atas run nyata, jadi hanya rasio antar T yang dipakai), FLOPs hanya menghitung matmul dan konvolusi, dan biaya ekstraksi fitur nyata per jendela belum diukur.

## 5. Hal yang ingin kami diskusikan

1. **T mana yang dipakai untuk perbandingan fusion (F1 `concat_glu` vs F2 `concat_fc`, lalu F3 dan F4)?** Usulan: **T = 10 sebagai T utama** (murah, lokalisasi `leave_event_out` terbaik) **ditambah satu T lebih besar (T = 30 atau 50)** sebagai pembanding, dan hasil dilaporkan lintas T supaya terlihat apakah urutan fusion konsisten. T = 60 tidak diusulkan (biaya tertinggi tanpa keuntungan lokalisasi).
2. **Skema untuk perbandingan fusion:** usulan `leave_event_out`, karena F1 dan F2 hanya berbeda arah di skema itu.
3. **Jumlah seed:** apakah cukup 3, atau dinaikkan ke 5 untuk perbandingan fusion.
4. **Ablasi modalitas** (trace, metrik, log sendiri-sendiri) untuk menguji hipotesis trace, dan **epoch lebih panjang** untuk T besar: apakah perlu dikerjakan sebelum F3/F4, atau sesudahnya.
