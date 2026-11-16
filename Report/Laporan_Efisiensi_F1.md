# Laporan Efisiensi: Baseline F1 (`concat_glu`) di Tiga Protokol

| | |
|---|---|
| Model | EADRO asli, fusion F1 `concat_glu` (concat → FC → GLU) |
| Data | Train Ticket (TT), `A1`, jendela T = 10 detik |
| Protokol | `within_event`, `leave_event_out`, `random_original` |
| Seed | 42, 7, 123 |
| Jumlah run | 9 (3 protokol × 3 seed) |
| Perangkat | Laptop, CPU i7-8650U (4 core / 8 thread), RAM 15 GiB, tanpa GPU |
| Sumber angka | Baris `Efficiency -- ...` dan `Epoch .../..., training loss: ... [xx s]` di `work/result/<hash>/running.log` (percobaan terakhir di tiap log) |
| Tujuan | Menjadi acuan efisiensi sebelum varian fusion lain (F2, F3, F4) dibandingkan |

Hasil efektivitas (F1, HR@k) untuk run yang sama ada di `Laporan_Eksperimen_Seed.md` (`within_event`, `leave_event_out`) dan `Laporan_Tingkat_A_Protokol_Asli.md` (`random_original`).

---

## 1. Cara pengukuran

Pengukuran dilakukan otomatis di akhir setiap training oleh fungsi `log_efficiency()` di `Eadro/codes/main.py`. Waktu training per epoch diambil dari log tiap epoch.

| Ukuran | Cara mengukur | Yang sebenarnya diukur |
|---|---|---|
| **Parameter total** | Jumlah semua bobot model (`p.numel()` untuk setiap parameter) | Ukuran model |
| **Parameter fusion** | Sama, hanya bobot dengan nama berawalan `fuse.` atau `fusion_module.` | Ukuran modul fusion saja |
| **Inferensi (ms/jendela)** | Model dalam mode evaluasi, tanpa gradien. 4 batch Val (± 1.024 jendela) disiapkan lebih dulu, 1 batch pemanasan, lalu waktu *forward pass* keempat batch diukur dengan `time.time()` dan dibagi jumlah jendela. Persiapan data dan pembuatan graf **tidak** ikut dihitung | Kecepatan model memproses satu jendela |
| **Memori puncak (MB)** | `resource.getrusage(RUSAGE_SELF).ru_maxrss / 1024` (satuan KB di Linux) | Memori tertinggi seluruh proses Python selama run, **termasuk data** |
| **Detik/epoch** | Rata-rata angka `[xx s]` di log tiap epoch | Waktu satu putaran training (termasuk pemuatan batch) |
| **Lama run** | Selisih waktu baris pertama log dan baris `Current hash_id` | Waktu total: memuat data, training, evaluasi |

---

## 2. Hasil per seed

| Protokol | Seed | Hash | Parameter total | Parameter fusion | Inferensi (ms/jendela) | Memori puncak (MB) | Epoch | Detik/epoch | Lama run (menit) |
|---|---|---|---|---|---|---|---|---|---|
| `within_event` | 42 | `fb3e4cc0` | 66.050 | 18.560 | 0,273 | 2.752 | 15 | 51,0 | 14,8 |
| `within_event` | 7 | `74f2db5a` | 66.050 | 18.560 | 0,263 | 2.752 | 15 | 51,1 | 14,9 |
| `within_event` | 123 | `dc38d8d0` | 66.050 | 18.560 | 0,266 | 2.753 | 15 | 50,7 | 14,8 |
| `leave_event_out` | 42 | `97e94b9a` | 66.050 | 18.560 | 0,270 | 2.787 | 15 | 58,7 | 17,0 |
| `leave_event_out` | 7 | `a8af9989` | 66.050 | 18.560 | 0,269 | 2.788 | 15 | 58,7 | 16,4 |
| `leave_event_out` | 123 | `9e7dfa9a` | 66.050 | 18.560 | 0,263 | 2.788 | 15 | 58,0 | 16,2 |
| `random_original` | 42 | `1c9748d6` | 66.050 | 18.560 | 0,270 | 3.562 | 50 | 79,2* | 70,1 |
| `random_original` | 7 | `9b5849e6` | 66.050 | 18.560 | 0,270 | 3.565 | 50 | 72,8 | 64,4 |
| `random_original` | 123 | `2f3b3cca` | 66.050 | 18.560 | 0,269 | 3.565 | 50 | 73,1 | 65,1 |

\* Seed 42 `random_original` lebih lambat di 19 epoch pertama (± 90 s/epoch, kemudian ± 72 s). Kemungkinan laptop sedang dipakai untuk pekerjaan lain saat itu.

---

## 3. Rata-rata ± sd per protokol (n = 3)

| Protokol | Jendela train | Inferensi (ms/jendela) | Memori puncak (MB) | Detik/epoch | Detik per 1.000 jendela train | Lama run (menit) |
|---|---|---|---|---|---|---|
| `within_event` | 40.510 | 0,268 ± 0,005 | 2.752 ± 1 | 50,9 ± 0,2 | 1,26 | 14,8 ± 0,1 |
| `leave_event_out` | 46.160 | 0,267 ± 0,003 | 2.788 ± 1 | 58,5 ± 0,4 | 1,27 | 16,5 ± 0,4 |
| `random_original` | 57.644 | 0,270 ± 0,000 | 3.564 ± 2 | 75,0 ± 3,6 | 1,30 (1,26 tanpa seed 42) | 66,5 ± 3,1 |

Pengaturan training: `within_event` dan `leave_event_out` 15 epoch, evaluasi tiap 5 epoch. `random_original` 50 epoch, evaluasi tiap 10 epoch.

---

## 4. Pembacaan

1. **Parameter identik di semua run** (66.050 total, 18.560 di fusion, atau 28% dari total). Parameter hanya ditentukan arsitektur, tidak bergantung pada data maupun seed.
2. **Waktu inferensi sama di ketiga protokol** (0,263–0,273 ms/jendela). Variasi ± 0,005 ms adalah gangguan pengukuran. Artinya, **selisih antar varian fusion di bawah sekitar 0,01 ms tidak boleh dianggap perbedaan nyata** dengan cara ukur ini.
3. **Waktu training sebanding dengan jumlah data, bukan protokolnya.** Setelah dibagi jumlah jendela train, ketiganya sekitar 1,26–1,27 detik per 1.000 jendela. `random_original` paling lama karena train-nya terbesar dan jumlah epochnya 50.
4. **Memori puncak mengikuti ukuran data, bukan model.** 2,75 / 2,79 / 3,56 GB, sedangkan bobot model hanya ± 0,26 MB (66.050 × 4 byte). `random_original` tertinggi karena train lebih besar dan Val/Test (salinan) dimuat dua kali.
5. **Ukuran yang paling bermakna untuk membandingkan fusion** adalah parameter fusion, parameter total, dan detik/epoch. Inferensi dan memori puncak kemungkinan hampir sama antar varian.

---

## 5. Keterbatasan pengukuran

1. **Memori puncak tidak mengukur fusion.** Angkanya didominasi data yang dimuat ke RAM. Semua varian kemungkinan menunjukkan memori hampir sama meskipun ukuran modelnya berbeda.
2. **Inferensi diukur sekali dengan sampel kecil** (4 batch). Cukup kasar untuk membedakan varian yang selisihnya kecil, dan peka terhadap aktivitas lain di laptop.
3. **Detik/epoch peka terhadap aktivitas laptop**, seperti terlihat pada seed 42 `random_original`.
4. **FLOPs (jumlah operasi hitung) belum diukur.**
5. **Hanya CPU.** Urutan efisiensi antar varian bisa berbeda di GPU.

---

## 6. Rencana perbaikan pengukuran

Setiap run menyimpan `model.ckpt`, jadi pengukuran yang lebih teliti bisa dilakukan **tanpa melatih ulang**, setelah semua varian fusion selesai dilatih:

1. Skrip benchmark terpisah memuat checkpoint setiap varian dan seed.
2. Inferensi diukur dengan lebih banyak batch, diulang beberapa kali, dan dilaporkan median serta sebarannya.
3. Memori diukur untuk model saja (bukan data), misalnya memori aktivasi saat *forward pass*.
4. FLOPs per jendela dihitung bila perlu.
5. Semua varian diukur dalam satu sesi dengan kondisi laptop yang sama, sehingga lebih adil.

Sampai skrip itu dibuat, varian baru (F2 dan seterusnya) diukur dengan cara yang sama seperti tabel di atas, supaya sebanding dengan F1.

---

## 7. Acuan untuk perbandingan F2

Perbandingan fusion dilakukan di `within_event`. Baris acuan F1:

| Ukuran | F1 `concat_glu` | F2 `concat_fc` (perkiraan dari arsitektur) |
|---|---|---|
| Parameter fusion | 18.560 | 9.280 (setengah) |
| Parameter total | 66.050 | ± 56.770 |
| Inferensi (ms/jendela) | 0,268 ± 0,005 | diukur |
| Memori puncak (MB) | 2.752 ± 1 | diukur (diperkirakan hampir sama) |
| Detik/epoch | 50,9 ± 0,2 | diukur |

Parameter total F2 adalah perkiraan: 66.050 − 18.560 + 9.280 = 56.770. Angka pastinya akan tercatat di log F2.

**Pembaruan 16 November 2026:** F2 sudah dijalankan. Parameter tercatat persis 56.770 total dan 9.280 fusion. Untuk seed 123 (satu-satunya seed yang seluruhnya memakai AC), hasilnya 51,0 s/epoch, 0,276 ms/jendela, dan 2.752 MB, praktis sama dengan F1. Seed 42 dan 7 diukur saat memakai baterai, sehingga waktunya tidak sebanding. Rincian ada di `Laporan_Fusion_F1_vs_F2.md`.

---

## Lampiran. Berkas terkait

| Berkas | Isi |
|---|---|
| `Eadro/codes/main.py` | Fungsi `log_efficiency()` |
| `work/result/<hash>/running.log` | Baris `Efficiency -- ...` dan waktu tiap epoch |
| `pipeline/rekap_seed.py` | Rekap rata-rata ± sd, termasuk tabel perbandingan fusion dengan kolom efisiensi |
| `Report/Laporan_Eksperimen_Seed.md` | Efektivitas `within_event` dan `leave_event_out` |
| `Report/Laporan_Tingkat_A_Protokol_Asli.md` | Efektivitas `random_original` |
