# Draft PPT: Progress 5

Status: **draft untuk disetujui**. Setelah di-acc, deck dibuat sebagai `Report/Progress 5.pptx` dari salinan `Progress 4.pptx` (gaya sama: EB Garamond / DM Sans, aksen 660000). `Progress 4.pptx` tidak diubah.

Isi: pekerjaan sejak Progress 4, yaitu (1) mengejar angka paper lewat protokol kode rilis EADRO, (2) baseline F1 lengkap di tiga protokol beserta efisiensinya, (3) eksperimen fusion pertama, F1 vs F2.

Format tiap slide: **Judul**, **Isi** (yang tampil di slide), **Visual** (grafik/tabel/diagram), **Catatan pembicara**.

Jumlah: 20 slide.

---

## Slide 1. Judul

**Judul:** Reproduksi Protokol Kode Rilis EADRO dan Perbandingan Fusion F1 vs F2

**Isi:**
- Progress 5, Mata Kuliah ML Multimodal
- Nama, tanggal

**Catatan pembicara:** Presentasi ini melanjutkan Progress 4. Dimulai dengan review singkat minggu lalu, lalu tiga bagian: menjawab permintaan mengejar angka paper, merangkum baseline F1 di tiga protokol, dan hasil perbandingan fusion pertama.

---

## Slide 2. Review Progress 4

**Isi:**

| Yang dikerjakan minggu lalu | Hasil singkat |
|---|---|
| Baseline EADRO dengan 3 seed (42, 7, 123) di dua cara bagi data | F1(std) 0,77 (`within_event`) dan 0,81 (`leave_event_out`); HR@1(std) 0,82 dan 0,65. Paper: 0,99 |
| Variasi antar seed | Seed saja menggeser HR@1 sampai 0,19 di `leave_event_out` (0,57–0,76) |
| Sumber masalah | Recall sudah tinggi (0,92–0,94), tetapi ± 60% jendela normal ikut dialarm |
| Jendela T = 5 vs T = 10 | Kualitas belum bisa dibedakan; T = 5 lebih ringan (−37% waktu/epoch, −23% RAM) |
| Data trace | Trace datang sebagai lonjakan 1 detik tiap ± 60 detik; hanya ± 18% jendela T = 10 memuat trace |

**Visual:** Tabel saja. Boleh ditambah grafik kecil hasil baseline dari Progress 4 (slide 5) di sisi kanan.

**Catatan pembicara:** Ringkasan cepat agar konteks minggu lalu tersambung. Inti minggu lalu: baseline kita jauh dari paper, masalah utamanya alarm palsu, dan variasi antar seed besar.

---

## Slide 3. Rencana minggu lalu dan tindak lanjutnya

**Isi:**

| Rencana / pertanyaan di Progress 4 | Tindak lanjut minggu ini |
|---|---|
| Diskusi: dekatkan baseline ke angka paper, atau cukup jelaskan selisihnya? | Dosen meminta angka paper dikejar → dijalankan **protokol kode rilis EADRO** (slide 5–8) |
| Tangani alarm palsu | **Sebagian**: dengan protokol kode rilis (bocor) alarm palsu turun dari ± 60% ke ± 6% (slide 7), jadi masalahnya muncul terutama pada data yang belum pernah dilihat. Di protokol tanpa kebocoran masih tinggi; F2 menurunkannya ke ± 40% (slide 14–15). Normalisasi alternatif belum dicoba |
| Perbandingan fusion dengan seed lebih banyak | **Dimulai**: F1 vs F2 di dua protokol, 3 seed (slide 12–18) |
| T lebih panjang (T = 30, T = 60) | **Ditunda**: prioritas dialihkan ke angka paper dan fusion; biaya T = 30 ± 4,6 jam, T = 60 ± 9 jam |

**Catatan pembicara:** Slide ini menunjukkan bahwa masukan minggu lalu ditindaklanjuti. Satu rencana ditunda dengan alasan biaya dan prioritas.

---

## Slide 4. Yang dikerjakan sejak Progress 4

**Isi:**

| Pekerjaan | Status |
|---|---|
| Protokol kode rilis EADRO (`random_original`) untuk mengejar angka paper | ✅ 3 seed, 50 epoch |
| Perbandingan teks paper vs kode rilis | ✅ Cara bagi data berbeda |
| Analisis metrik HR@k kode rilis | ✅ Ditemukan cacat rumus |
| Pengukuran efisiensi baseline F1 (9 run) | ✅ |
| Acceptance check baseline | ✅ 4 terpenuhi, 1 sebagian |
| Fusion F2 (`concat_fc`) di `within_event` dan `leave_event_out` | ✅ 3 seed per protokol |
| Fusion F3 dan F4 | ⏳ Menunggu paper rujukan |

**Catatan pembicara:** Total 15 run training baru: 3 run protokol kode rilis dan 6 run F2, ditambah analisis ulang 6 run baseline.

---

## Slide 5. Paper dan kode rilis EADRO tidak sepakat

**Isi:**

**Teks paper** (Bagian V.A *Data Collection*, hlm. 7):
> "Data produced in different periods are divided into training (60%) data and testing (40%) data, respectively."

Tidak ada kata *random* atau *shuffle* untuk pembagian data; validation set dan cara memilih epoch tidak disebut.

**Kode rilis** (`Eadro/`, commit asli `03ab600`):

| Bukti | Lokasi | Isi |
|---|---|---|
| Jendela bergeser 1 detik | `codes/preprocess/align.py` baris 23–24 | `for s in range(start, end-chunk_lenth+1)` |
| Diacak per jendela, tanpa seed | `codes/preprocess/align.py` baris 133–138 | `np.random.shuffle(chunk_idx)` lalu dipotong train/test |
| Rasio 70/30, bukan 60/40 | `codes/preprocess/align.py` baris 174 | `--test_ratio`, default `0.3` |
| Tanpa Val; epoch dipilih pakai **Test** | `codes/base.py` baris 101–105 | `test_results = self.evaluate(test_loader, ...)`; simpan model bila `HR@1` Test lebih tinggi |

| | Teks paper | Kode rilis |
|---|---|---|
| Cara bagi | Per periode waktu | Acak per jendela |
| Rasio | 60/40 | 70/30 |
| Pemilihan epoch | Tidak disebut | Pakai Test |

**Visual:** Dua kotak berdampingan: kiri kutipan paper, kanan potongan kode `align.py` dengan baris `np.random.shuffle` disorot.

**Catatan pembicara:** Paper menulis pembagian per periode, tetapi kode yang dirilis membagi secara acak per jendela dan memilih epoch pakai Test. Pembagian per waktu kita (`within_event`) adalah yang paling dekat dengan teks paper. Karena kita tidak tahu protokol mana yang menghasilkan angka paper, kita uji protokol kode rilis secara langsung.

---

## Slide 6. Mengapa menguji protokol kode rilis?

**Isi:**
- Angka kita (F1(std) ± 0,77–0,81) jauh di bawah paper (F1 0,989).
- Pertanyaan: apakah selisihnya dari **model/data** kita, atau dari **cara membagi data**?
- Uji: jalankan ulang dengan cara bagi data persis seperti **kode rilis** EADRO (skema `random_original`).

| | Protokol kita (`within_event`, `leave_event_out`) | Protokol kode rilis (`random_original`) |
|---|---|---|
| Cara bagi data | Per waktu / per kejadian gangguan, dengan jeda pemisah | Acak per jendela, 70/30 |
| Jendela bertetangga | Tidak pernah di split berbeda | Tersebar di Train dan Test (beririsan 9 dari 10 detik) |
| Pemilihan epoch | Pakai Val | Pakai **Test** (Val = salinan Test) |
| Kebocoran data | Tidak ada | Ada |

**Visual:** Diagram dua baris garis waktu satu run. Atas: blok Train | Val | Test berurutan (`within_event`). Bawah: jendela diwarnai acak Train/Test (`random_original`).

**Catatan pembicara:** Ini menjawab permintaan dosen untuk mengejar angka paper. Tujuannya bukan mengganti protokol kita, tetapi menguji dari mana selisih itu berasal.

---

## Slide 7. Hasil protokol kode rilis vs paper

**Isi:**

| Ukuran | Paper (TT) | Kita, epoch terpilih | Kita, epoch 49 |
|---|---|---|---|
| F1 | 0,989 | 0,923 ± 0,009 | **0,964 ± 0,001** |
| Precision | 0,984 | 0,873 | **0,961** |
| Recall | 0,995 | 0,980 | 0,966 |
| HR@1 | 0,990 | **0,975 ± 0,014** | 0,963 ± 0,013 |
| Alarm palsu (FPR) | – | – | 5,9% ± 1,4% |

Metrik versi standar (std), 3 seed (42, 7, 123), 50 epoch.

- Dengan protokol kode rilis, angka kita **mendekati paper**.
- Alarm palsu turun dari ± 60% (protokol kita) ke ± 6%.

**Visual:** Grafik batang berkelompok: F1, Precision, Recall, HR@1 untuk tiga kelompok (paper, `within_event`, `random_original` epoch 49).

**Catatan pembicara:** Model dan data kita sama, hanya cara bagi datanya yang berbeda. Artinya selisih besar ke paper terutama berasal dari protokol yang bocor, bukan dari kesalahan pipeline kita. Ini juga mendukung dugaan bahwa angka paper dihasilkan dengan pembagian acak seperti di kodenya, walaupun teks paper menulis pembagian per periode; dugaan ini tidak bisa dipastikan. Sisa selisih (± 0,02–0,03) wajar karena data publik hanya 81 injeksi, sedangkan paper menyebut 162.

---

## Slide 8. Temuan: rumus HR@k kode rilis cacat

**Isi:**
- Kode rilis menghitung jendela **normal yang ditebak normal** sebagai TP.
- HR@k asli = hit / (TP + FN). Penyebutnya ikut memuat jendela normal yang benar.

| Bukti | Lokasi (`Eadro/`, commit `03ab600`) | Isi |
|---|---|---|
| Normal yang ditebak normal dihitung TP | `codes/base.py` baris 37 | `if faulty_nodes[0] == -1: TP+=1` (untuk jendela normal) |
| Penyebut HR@k | `codes/base.py` baris 50 dan 57 | `pos = TP+FN`; `HR@k = hrs[k-1] / pos` |
| Epoch dipilih dengan HR@k ini | `codes/base.py` baris 103–104 | `if test_results["HR@1"] > best_hr1: ...` |

- Akibatnya: **makin sedikit alarm palsu, makin rendah HR@k asli.**
- Batas atas HR@1 asli di data kita: 14.779 / 24.705 = **0,598**, walaupun model sempurna.
- Terverifikasi tepat di 15 dari 15 titik: HR@1 asli = HR@1(std) × n_gangguan / (n_gangguan + n_normal − FP).
- Agar HR@1 asli 0,99 dengan Precision 0,984, Test paper harus berisi **≤ ± 2,6% jendela normal**.

**Keputusan:** semua perbandingan memakai metrik **(std)**, yang hanya menghitung kelas gangguan.

**Catatan pembicara:** Ini juga menjelaskan mengapa HR@1 asli kita sekitar 0,6. Angka paper kemungkinan berasal dari data uji dengan sangat sedikit jendela normal, atau dari rumus yang berbeda dengan kode yang dirilis.

---

## Slide 9. Baseline F1 di tiga protokol

**Isi:**

| Protokol | F1(std) | Precision(std) | Recall(std) | HR@1(std) | Bocor? |
|---|---|---|---|---|---|
| `within_event` | 0,767 ± 0,017 | 0,658 | 0,923 | 0,822 ± 0,031 | Tidak |
| `leave_event_out` | 0,806 ± 0,036 | 0,706 | 0,938 | 0,650 ± 0,099 | Tidak |
| `random_original` | 0,923 ± 0,009 | 0,873 | 0,980 | 0,975 ± 0,014 | Ya |
| Paper (TT) | 0,989 | 0,984 | 0,995 | 0,990 | – |

`within_event` dan `leave_event_out`: 15 epoch, pilih epoch dengan `combo`. `random_original`: 50 epoch, pilih epoch dengan HR@1 asli di Test (seperti kode rilis).

**Catatan pembicara:** `within_event` menguji event yang sudah pernah dilihat. `leave_event_out` menguji gangguan baru, sehingga lokalisasinya paling sulit. `random_original` hanya pembanding untuk paper. Hasil per seed ada di laporan.

---

## Slide 10. Efisiensi baseline F1

**Isi:**

| Protokol | Parameter (total / fusion) | Inferensi (ms/jendela) | Memori puncak | Detik/epoch |
|---|---|---|---|---|
| `within_event` | 66.050 / 18.560 | 0,268 ± 0,005 | 2,75 GB | 50,9 ± 0,2 |
| `leave_event_out` | 66.050 / 18.560 | 0,267 ± 0,003 | 2,79 GB | 58,5 ± 0,4 |
| `random_original` | 66.050 / 18.560 | 0,270 ± 0,000 | 3,56 GB | 75,0 ± 3,6 |

- Diukur otomatis di akhir training (`log_efficiency()`).
- Waktu training sebanding dengan jumlah data: ± 1,26 detik per 1.000 jendela train di semua protokol.
- Memori puncak didominasi **data**, bukan model (bobot model hanya ± 0,26 MB).
- Selisih inferensi < 0,01 ms termasuk gangguan pengukuran.

**Catatan pembicara:** Angka ini menjadi acuan untuk semua varian fusion. Karena memori didominasi data, ukuran yang paling bermakna untuk membandingkan fusion adalah jumlah parameter dan waktu.

---

## Slide 11. Acceptance check baseline

**Isi:**

| Kriteria | Status | Bukti |
|---|---|---|
| Pipeline Correctness | ✅ | Setiap tahap data diverifikasi dengan fungsi asli EADRO; 7 bug kode asli diperbaiki |
| Architectural Fidelity | ✅ | Arsitektur sama dengan paper (encoder per modalitas, concat → FC → GLU, GATv2, detector dan localizer) |
| Experimental Consistency | ⚠️ Sebagian | 3 seed dan pengaturan dicatat; tetapi Val `within_event` tidak mewakili Test, dan pengaturan `random_original` berbeda dari dua protokol lain |
| Training Stability | ✅ | Tanpa NaN; training deterministik (run ulang seed sama → hasil identik) |
| Performance Sanity Check | ✅ | Protokol kode rilis mendekati paper; jauh di atas tebakan acak (HR@1 ≈ 0,037) |

**Catatan pembicara:** Satu kriteria hanya terpenuhi sebagian. Keterbatasan ini berlaku sama untuk semua varian fusion, jadi perbandingan antar fusion tetap adil.

---

## Slide 12. Kandidat fusion dan statusnya

**Isi:**

| Kode | Mekanisme | Rujukan | Status |
|---|---|---|---|
| F1 | Concat + FC + GLU | EADRO (baseline) | ✅ 3 protokol |
| F2 | Concat + FC (tanpa GLU) | Ablation EADRO | ✅ `within_event`, `leave_event_out` |
| F3 | Learnable Weighted Feature Fusion | MULAN, Topo-MFP | ⏳ Menunggu paper rujukan |
| F4 | Cross-Attention Feature Fusion | FAMOS | ⏳ Menunggu paper rujukan |

- Urutan eksperimen: `within_event` → `leave_event_out` → `random_original`.
- Semua varian memakai pengaturan identik; hanya modul fusion yang berbeda.

**Catatan pembicara:** Antarmuka fusion dibuat seragam: tiga keluaran encoder per layanan masuk, satu representasi keluar. Jadi varian bisa diganti tanpa mengubah bagian lain model.

---

## Slide 13. F1 vs F2: apa bedanya?

**Isi:**

| | F1 `concat_glu` | F2 `concat_fc` |
|---|---|---|
| Alur | gabung 3 modalitas (144) → FC 144→128 → **GLU** → 64 | gabung 3 modalitas (144) → FC 144→64 → ReLU |
| Parameter fusion | 18.560 | 9.280 (−50%) |
| Parameter total | 66.050 | 56.770 (−14%) |

- GLU = "gerbang" yang belajar menyaring fitur mana yang diteruskan.
- Pertanyaan: **apakah gerbang ini benar-benar diperlukan?**

**Visual:** Diagram dua alur berdampingan, dengan blok GLU disorot di alur F1.

**Catatan pembicara:** F2 adalah ablation: komponen GLU dibuang, sisanya dipertahankan. Paper EADRO tidak pernah menguji ini.

---

## Slide 14. Hasil `within_event` (event yang sudah dikenal)

**Isi:**

| Ukuran | F1 | F2 | Selisih |
|---|---|---|---|
| F1(std) | 0,767 ± 0,017 | **0,818 ± 0,031** | +0,051 |
| Precision(std) | 0,658 | **0,736** | +0,078 |
| Recall(std) | 0,923 | 0,923 | 0 |
| HR@1(std) | 0,822 | 0,842 | +0,021 |
| Alarm palsu (FPR) | 61,6% | **42,2%** | −19 poin |

- Deteksi: F2 sedikit lebih baik karena **alarm palsu berkurang**.
- Lokalisasi: setara.
- Belum pasti: seed 42 tidak membaik; uji-t p ≈ 0,2.

**Visual:** Grafik batang berkelompok F1 vs F2 untuk F1(std), Precision, Recall, HR@1, dengan error bar sd.

**Catatan pembicara:** Kalau hanya melihat protokol ini, kesimpulannya "GLU tidak perlu". Slide berikut menunjukkan kenapa kesimpulan itu terlalu cepat.

---

## Slide 15. Hasil `leave_event_out` (gangguan baru)

**Isi:**

| Ukuran | F1 | F2 | Selisih |
|---|---|---|---|
| F1(std) | 0,806 ± 0,036 | 0,827 ± 0,066 | +0,021 |
| Precision(std) | 0,706 | **0,778** | +0,072 |
| Recall(std) | **0,938** | 0,884 | −0,055 |
| HR@1(std) | **0,650 ± 0,099** | 0,509 ± 0,084 | **−0,141** |
| HR@3(std) | **0,754** | 0,592 | −0,163 |
| Alarm palsu (FPR) | 59,0% | **37,7%** | −21 poin |

- Deteksi: seimbang (alarm palsu turun, tetapi lebih banyak gangguan terlewat).
- Lokalisasi: **F2 jelas lebih buruk**, turun di ketiga seed.

**Visual:** Grafik batang yang sama seperti slide 14, supaya mudah dibandingkan.

**Catatan pembicara:** Penurunan HR@1 bukan sekadar akibat lebih banyak gangguan terlewat. Dihitung hanya dari gangguan yang terdeteksi pun, F2 tetap lebih rendah (0,574 vs 0,690).

---

## Slide 16. Temuan kunci: GLU membantu pada gangguan baru

**Isi:**

HR@1(std) di `leave_event_out`, semua epoch yang tercatat:

| Seed | F1, epoch **terburuk** | F2, epoch **terbaik** |
|---|---|---|
| 42 | 0,524 | 0,419 |
| 7 | 0,624 | 0,587 |
| 123 | 0,674 | 0,594 |

- Di setiap seed, epoch terbaik F2 masih di bawah epoch terburuk F1.
- Di Val (event yang mirip Train), lokalisasi keduanya sama (0,76–0,94). Perbedaan baru muncul di **event yang belum pernah dilihat**.
- Dugaan (belum diuji): gerbang GLU membantu memilih fitur yang lebih umum dari ketiga modalitas.

**Visual:** Dot plot per seed: titik HR@1(std) F1 dan F2 di setiap epoch, dihubungkan garis per varian.

**Catatan pembicara:** Ini bukti terkuat dalam perbandingan ini. Uji-t formal belum signifikan (p ≈ 0,13, n = 3), tetapi arahnya konsisten di semua seed dan semua epoch.

---

## Slide 17. Efisiensi F1 vs F2

**Isi:**

| Ukuran | F1 | F2 |
|---|---|---|
| Parameter fusion | 18.560 | **9.280** |
| Parameter total | 66.050 | **56.770** |
| Detik/epoch (`within_event` / `leave_event_out`) | 50,9 / 58,5 | 51,0 / 58,5 |
| Inferensi (ms/jendela) | 0,268 / 0,267 | 0,276 / 0,270 |
| Memori puncak | 2,75 / 2,79 GB | 2,75 / 2,79 GB |

- Model lebih kecil, tetapi **tidak lebih cepat**.
- Fusion hanya sebagian kecil komputasi. Waktu lebih banyak habis di encoder modalitas, GAT, dan pemuatan data.

**Catatan pembicara:** Angka waktu F2 `within_event` diambil dari seed 123 saja, karena dua seed lain berjalan saat laptop memakai baterai (CPU melambat). Hasil efektivitas tidak terpengaruh karena training deterministik.

---

## Slide 18. Kesimpulan F1 vs F2

**Isi:**

| Protokol | Deteksi | Lokalisasi |
|---|---|---|
| `within_event` (event dikenal) | F2 sedikit lebih baik | Setara |
| `leave_event_out` (gangguan baru) | Seimbang | **F1 lebih baik** (+0,14 HR@1) |

- F2 konsisten **mengurangi alarm palsu** (± 20 poin persen) di kedua protokol.
- **GLU membantu lokalisasi akar masalah pada gangguan yang belum pernah dilihat.**
- Menghapus GLU menghemat 50% parameter fusion, tetapi tanpa percepatan yang terukur.
- Pelajaran metodologis: menguji di satu protokol saja bisa menghasilkan kesimpulan yang keliru.

**Catatan pembicara:** Untuk deployment nyata, gangguan baru adalah skenario yang paling penting. Jadi GLU layak dipertahankan, dan varian F3/F4 perlu diuji terutama di `leave_event_out`.

---

## Slide 19. Keterbatasan

**Isi:**
1. **Hanya 3 seed.** Variasi antar seed (sd HR@1 ± 0,1 di `leave_event_out`) sebesar efek yang dicari.
2. **Val `within_event` tidak mewakili Test** (Val combo ± 0,96 vs Test ± 0,82).
3. **Alarm palsu masih tinggi** di protokol tanpa kebocoran (± 40–60% jendela normal).
4. **Waktu diukur sekali per run** dan peka terhadap kondisi laptop.
5. **Analisis per jenis gangguan dan per layanan belum dilakukan.**
6. **F2 di `random_original` belum dijalankan.**

---

## Slide 20. Rencana berikutnya

**Isi:**

| Langkah | Perkiraan waktu |
|---|---|
| Implementasi F3 (Learnable Weighted) dan F4 (Cross-Attention) sesuai paper rujukan | Setelah paper diterima |
| F3 dan F4 di `within_event` dan `leave_event_out` (3 seed) | ± 1,7 jam per varian |
| Semua varian di `random_original` | ± 3¼ jam per varian (3 seed) atau ± 65 menit (1 seed) |
| Seed tambahan untuk semua varian (2 seed lagi, total 5) | ± 35 menit per varian per protokol |
| Skrip benchmark efisiensi dari `model.ckpt` (semua varian, kondisi sama) | Tanpa training ulang |

**Pertanyaan diskusi:**
- Apakah `leave_event_out` disetujui sebagai protokol utama untuk kesimpulan fusion?
- Apakah 3 seed cukup, atau perlu 5?

**Catatan pembicara:** Dua pertanyaan ini menentukan berapa banyak komputasi yang dibutuhkan untuk tahap berikutnya.

---

## Catatan untuk implementasi

- **Grafik yang perlu dibuat** (matplotlib, palet sama seperti Progress 4):
  1. Slide 7: batang berkelompok paper vs `within_event` vs `random_original`.
  2. Slide 14 dan 15: batang berkelompok F1 vs F2 dengan error bar.
  3. Slide 16: dot plot HR@1 per seed per epoch.
- **Diagram:** slide 5 (kutipan paper vs potongan kode), slide 6 (dua cara bagi data) dan slide 13 (alur F1 vs F2), dibuat dengan bentuk PowerPoint.
- **Sumber angka:** `Laporan_Tingkat_A_Protokol_Asli.md`, `Laporan_Eksperimen_Seed.md`, `Laporan_Efisiensi_F1.md`, `Laporan_Fusion_F1_vs_F2.md`.
- Slide 9 dan 12 bisa digabung jika deck perlu dipersingkat. Slide 8 bisa dipindah ke lampiran jika waktu presentasi terbatas.
- Slide 2 dan 3 (review minggu lalu) sebaiknya dibawakan cepat, ± 1 menit total.
