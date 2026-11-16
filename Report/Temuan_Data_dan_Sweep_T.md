# Temuan Data Trace dan Rencana Eksplorasi Panjang Jendela (T)

| | |
|---|---|
| Dibuat | 10 November 2026, dini hari WIB |
| Cakupan | Dataset Train Ticket (TT) saja. Social Network (SN) di luar cakupan |
| Dokumen pendamping | `Report/Laporan_Eksperimen_Seed.md` (baseline 3 seed, T = 10) |
| Isi | Temuan tentang jumlah dan pola trace, cakupan jendela per T, saran dosen, biaya komputasi terukur per T, rencana sweep, dan pertanyaan yang belum diputuskan |

Bagian yang berisi **hasil terukur**, **perkiraan**, dan **dugaan yang belum diverifikasi** dipisahkan secara eksplisit. Skrip yang menghitung angka-angka di bagian 2–3 dulu disimpan di folder sementara sesi dan **tidak tersimpan di proyek**. Metodenya dijelaskan di tiap bagian sehingga bisa dihitung ulang.

---

## 1. Ringkasan

1. **Jumlah trace di data kita tidak jauh berbeda dari paper bila "trace" dihitung sebagai span.** Trace unik: 8.577. Span unik: 50.172. Paper melaporkan 48.296 trace TT. Selisih span dengan paper hanya 3,9%. Dugaan awal saya bahwa "data kita separuh paper" tidak didukung pengukuran dan sudah dicabut.
2. **Trace di data kita datang dalam lonjakan 1 detik tiap ±60 detik, bukan merata.** Ini berbeda dari deskripsi paper (0,2–0,5 permintaan per detik, merata). Pada T = 10 hanya ±18% jendela memuat satu pun span.
3. **Cakupan trace per jendela kira-kira sebanding dengan T/60.** Di antara nilai T yang dihitung (3, 5, 10, 20, 30, 60), hanya T = 60 yang hampir semua jendelanya (95%) memuat lonjakan. Itu menjadikan T = 60 titik penting dalam sweep.
4. **Biaya komputasi naik hampir linear terhadap T.** Dari pengukuran: T = 5 butuh ±30 menit untuk 3 seed, sedangkan T = 60 diperkirakan ±9 jam dan berisiko kehabisan RAM.
5. **Saran dosen** (3 seed, T lebih kecil dan lebih besar) sudah mulai dijalankan: 3 seed selesai untuk T = 10 dan T = 5.
6. **Hasil T = 5 (bagian 10): tidak berbeda nyata dari T = 10** dengan 3 seed. Semua selisih kecil (F1 −0,024; HR@1 −0,023) dan semua selang kepercayaan selisih mencakup nol. Pembacaan dari seed 42 saja (Precision turun 0,14) tidak bertahan setelah 3 seed. T = 5 lebih ringan: 32 detik per epoch (T = 10: 51) dan RAM 2,1 GB (T = 10: 2,75 GB).

---

## 2. Temuan jumlah trace

### 2.1 Pertanyaan

Dalam paper, TT dilaporkan memiliki 162 injeksi dan 48.296 trace. Data publik TT yang kita punya berisi 81 injeksi (9 run berfault × 9 injeksi, tiap pasangan service dan jenis fault satu kali) dan 3 run tanpa fault. Apakah selisih performa dengan paper sebagian berasal dari jumlah data yang lebih sedikit?

### 2.2 Hasil pengukuran

Cara hitung: trace dan span dihitung per ID unik di dalam rentang waktu 12 run (9 berfault + 3 tanpa fault).

| Ukuran | Nilai |
|---|---|
| Trace unik di dalam jendela 12 run | **8.577** |
| ... dari 9 run berfault | 5.751 |
| ... dari 3 run tanpa fault | 942 per run (2.826 total) |
| Trace unik tanpa filter jendela | 9.320 |
| Span unik di dalam jendela | **50.172** (client 20.804; server 29.363) |
| Laju trace | ±0,104 trace per detik |
| Paper (TT) | 48.296 "trace"; laju 0,2–0,5 permintaan per detik |

Catatan: jumlah client dan server (50.167) berbeda 5 dari total span (50.172). Selisih kecil itu tidak saya telusuri.

### 2.3 Pembacaan

- Jika "trace" diartikan sebagai trace unik, data kita **5,6 kali lebih sedikit** dari paper.
- Jika diartikan sebagai **span**, selisihnya hanya **3,9%** (50.172 vs 48.296).
- Paper tidak menjelaskan satuan hitungnya, jadi **belum pasti** mana yang tepat. Yang bisa dikatakan: ukuran data bukan penjelasan yang jelas atas selisih performa.

### 2.4 Hal yang belum dipastikan

Ketiga run tanpa fault memiliki jumlah **identik**: 942 trace, 5.522 span, 2.290 client. ID-nya berbeda. Konsisten dengan beban kerja yang deterministik (bagian 3), tetapi belum diperiksa apakah itu murni beban kerja otomatis atau data yang tersalin.

---

## 3. Temuan pola waktu trace: lonjakan tiap ±60 detik

### 3.1 Pengamatan (terverifikasi pada 12 run)

| Ukuran | Nilai |
|---|---|
| Median jeda antar lonjakan | **60 detik** (sama di 12 dari 12 run) |
| Median lebar lonjakan | 1 detik |
| Detik yang memuat span client | hanya 89–202 dari ±6.461 detik per run |
| Run tanpa fault | 135 lonjakan × ±7 trace = 942 trace |

Angka 135 × ±7 menjelaskan mengapa jumlah trace di tiga run tanpa fault identik. Penjelasan ini konsisten dengan data, tapi belum dibuktikan secara langsung.

Ini **berbeda dari deskripsi paper**, yang menyebut beban kerja merata (0,2–0,5 permintaan per detik). Di data kita, beban kerja berupa kiriman serempak sekali per menit.

### 3.2 Konsekuensi untuk model

Fitur trace per service adalah deret waktu latensi rata-rata per slot 1 detik. Karena lonjakan hanya 1 detik tiap 60 detik:

- Tiap deret service **±98,5% berisi nol**. Pada T = 10 rata-rata hanya 0,15 slot dari 10 yang terisi; pada T = 60 rata-rata 0,93 slot dari 60.
- Melebarkan slot (mis. 5 detik per slot) **tidak menambah kepadatan**, karena lonjakan itu sendiri hanya 1 detik lebarnya.
- Hanya 9 service (27 dari 81 fault) yang biangnya punya trace sama sekali. Untuk 54 fault lain, modalitas trace pada service biang selalu kosong.

Konsekuensinya: probabilitas sebuah jendela memuat setidaknya satu lonjakan ≈ **T / 60**.

---

## 4. Cakupan jendela per T

Jendela berstride 1 (jendela bergeser 1 detik). Persentase jendela yang memuat setidaknya satu span:

| T (detik) | 3 | 5 | 10 | 20 | 30 | 60 |
|---|---|---|---|---|---|---|
| Pada setidaknya satu service | 6,0% | 9,6% | **18,3%** | 34,5% | 49,9% | **95,3%** |
| Pada satu service ber-trace (9 service) | 4,6% | 7,6% | 15,1% | 30,0% | 44,9% | 89,4% |

### Komposisi label (threshold 1 detik tumpang tindih)

| T | Jendela gangguan | Normal di celah antar fault | Normal di run tanpa fault |
|---|---|---|---|
| 10 | 49.355 | 8.713 | 24.294 |
| 60 | 52.955 | 4.663 (turun 46%) | 24.144 |

Aturan labelnya: jendela diberi label "gangguan" bila ada tumpang tindih 1 detik saja dengan fault. Dengan T yang lebih besar, makin banyak jendela perbatasan yang berlabel gangguan, dan jendela normal di celah makin sedikit.

### Implikasi yang perlu dicatat

1. **Jendela normal di celah adalah sumber utama alarm palsu** (bagian 6.2 laporan seed). Jumlahnya berubah menurut T, sehingga komposisi kelas dan metrik per jenis normal sebaiknya dilaporkan bersama hasil tiap T.
2. **Jendela yang melintasi batas train/val/test dibuang.** Jumlah yang dibuang berubah menurut T: pada `within_event` 2.160 (T = 10) dan 960 (T = 5).
3. **Jendela bertetangga makin mirip pada T besar.** Pada T = 60 dua jendela berurutan bertumpuk 59 dari 60 detik, sehingga sampel makin tidak independen.

### Hipotesis yang bisa diuji (bukan hasil)

Modalitas trace hanya memberi sinyal bila jendelanya cukup panjang menangkap lonjakan. Jadi bila hipotesis benar, T lebih besar seharusnya membantu lokalisasi dan deteksi. T = 5 sudah dijalankan (bagian 10) dan tidak berbeda nyata dari T = 10, jadi hasilnya belum mendukung maupun menolak hipotesis ini. Pengujian yang berarti menunggu T = 30 dan T = 60. Hipotesis ini **belum diuji**.

---

## 5. Saran dosen dan rencana

### 5.1 Saran dosen (10 November 2026)

1. Gunakan **3 seed berbeda**.
2. Eksplorasi **windowing yang lebih sedikit dan lebih banyak**.

### 5.2 Status eksekusi

| Saran | Status |
|---|---|
| 3 seed pada T = 10 (kedua skema) | **Selesai** (10 Nov, 00.38–02.13). Lihat `Laporan_Eksperimen_Seed.md` |
| T = 5, skema `within_event`, 3 seed | **Selesai** (10 Nov, 04.11–04.41). Hasil di bagian 10 |
| T = 30 | Belum dijalankan |
| T = 60 | Belum dijalankan (butuh keputusan soal RAM dan stride, bagian 6.3) |

### 5.3 Desain yang dijalankan

- Hanya T yang berubah. Seluruh pengaturan lain sama dengan baseline T = 10: 15 epoch, `combo`, `eval_every = 5`, seed 42/7/123, `concat_glu`, `lr = 0,001`, batch 256.
- Skema `within_event` dulu, karena lebih murah dan variasinya antar seed lebih kecil (sd HR@1 ≈ 0,03 dibanding 0,10 di `leave_event_out`). Skema `leave_event_out` hanya perlu dijalankan untuk T yang efeknya melebihi sd.
- Setiap T dibangun dan dilatih **terpisah** sebagai dataset sendiri (`A1_T<T>`), sehingga data T = 10 tidak tertimpa dan urutan pengerjaan bebas.

### 5.4 Cara menjalankan satu T

```bash
cd "/home/ojan/AI Labs/EADRO - APDM"
nohup systemd-inhibit --what=sleep:idle --who="EADRO T5" bash -c '
  pipeline/build_T.sh 5 within_event &&
  DATA_NAME=A1_T5 pipeline/run_grid.sh within_event 15 "42 7 123" "concat_glu"
' > train_T5.out 2>&1 &
```

Ganti `5` dan `A1_T5` dengan T yang diinginkan. Hasil per T muncul sebagai grup `A1_T<T>/within_event` pada `python3 -I pipeline/rekap_seed.py work/result`.

---

## 6. Biaya komputasi per T

### 6.1 Waktu satu langkah latih (benchmark, data acak)

Benchmark mikro (±1 menit): forward, backward, dan Adam pada batch 256, 4 thread CPU, tanpa menyimpan apa pun.

| T | Detik per langkah | Tensor per jendela |
|---|---|---|
| 5 | 0,208 | 10,5 KB |
| 10 | 0,348 | 14,8 KB |
| 30 | 1,097 | 31,6 KB |
| 60 | 2,281 | 57,0 KB |

Kalibrasi: untuk T = 10 benchmark memprediksi 55 detik per epoch, sedangkan run nyata 51 detik.

### 6.2 Waktu per run dan per sweep

| T | Detik per epoch | Waktu per run (15 epoch + evaluasi) | 3 seed `within_event` | Sumber |
|---|---|---|---|---|
| 5 | 32 | 10 menit | ±30 menit | **Terukur** |
| 10 | 51 | 15 menit | ±45 menit | **Terukur** |
| 30 | ±160 | ±47 menit | ±2,4 jam | Perkiraan dari benchmark |
| 60 | ±340 | ±97 menit | ±4,9 jam | Perkiraan dari benchmark |

Skema `leave_event_out` sekitar 14% lebih lama (lebih banyak jendela latih).

### 6.3 Biaya membangun data (cache)

Fitur log (Hawkes) memakan sebagian besar waktu build.

| T | Tahap `logs` per run | Total build 12 run (4 paralel) | Sumber |
|---|---|---|---|
| 5 | 205–399 detik | **23 menit** (03.47–04.11) | **Terukur** |
| 10 | 15–37 menit (8 proses serentak di 4 core; run tanpa fault paling lama) | ±47 menit (20.53–21.39) | Dari cap waktu berkas cache, bukan log |
| 30 | | ±2,2 jam | Ekstrapolasi linear |
| 60 | | ±4,4 jam | Ekstrapolasi linear |

Build T = 10 memakan ±2× waktu T = 5, dan itu mendukung asumsi linear. Itu hanya dua titik, dan kondisi paralelismenya berbeda. Ekstrapolasi untuk T = 30 dan T = 60 **belum teruji**.

Run tanpa fault (idx 9–11) berisi 8.102 jendela, lebih banyak daripada run berfault (6.456 jendela pada T = 5), dan selesai belakangan.

### 6.4 Total per T (build + 3 seed `within_event`)

| T | Total |
|---|---|
| 5 | ±55 menit (terukur) |
| 30 | ±4,6 jam (perkiraan) |
| 60 | ±9,3 jam (perkiraan) |

### 6.5 RAM

- Mesin: Linux, Intel i7-8650U (4 core fisik, 8 thread), RAM 15 GB (±10–11 GB bebas), tanpa GPU.
- Peak RSS terukur: T = 5 → 2.131 MB; T = 10 → 2.752 MB.
- Untuk T = 60: tensor 57 KB × ±80 ribu jendela ≈ 4,6 GB, lalu ditambah salinan saat memuat dan overhead torch/dgl. Perkiraan puncak ±10–11 GB, **sangat mepet dengan RAM bebas**. Ini perkiraan yang belum diukur.
- T = 30 diperkirakan ±5–6 GB (aman).

### 6.6 Opsi untuk T = 60

- **Stride lebih besar** (mis. 5): memangkas waktu dan RAM sekitar 5×, tetapi mengubah jumlah sampel latih. Stride saat ini keras 1 di pembuat jendela, jadi perlu perubahan kode, dan perubahan itu harus dicatat sebagai perbedaan desain.
- **Satu seed untuk penyaringan** terlebih dahulu.
- **Dilewati**, dan T = 30 dipakai sebagai batas atas.

---

## 7. Yang berubah selain T

T bukan satu-satunya yang berubah bila T diganti. Perlu dicatat di laporan hasil sweep:

1. **Jumlah parameter model.** T = 5: 65.400 parameter; T = 10: 66.050 (selisih 650, ≈ 1%). Dugaan saya, lapisan self-attention memiliki bobot per posisi waktu. Dugaan itu belum dicek di kode.
2. **Jumlah jendela yang dibuang** (purge) pada tiap batas split.
3. **Komposisi label**, terutama jendela normal di celah (bagian 4).
4. **Kelas normal berasal dari dua sumber:** celah antar fault dan run tanpa fault. Proporsinya berubah menurut T.

---

## 8. Pertanyaan yang belum diputuskan

| # | Pertanyaan | Catatan |
|---|---|---|
| 1 | Apa definisi sukses baseline: baseline jujur dengan selisih yang dijelaskan, atau mencocokkan angka paper? | Belum dijawab. Ini menentukan seberapa jauh protokol dilonggarkan |
| 2 | Apakah tingkat A dijalankan (protokol acak dari kode asli, sebagai batas atas diagnostik)? | Hanya diagnostik, bukan baseline. Protokol itu bocor waktu |
| 3 | Apakah run tanpa fault tetap menjadi kelas normal? | Mempengaruhi alarm palsu |
| 4 | Himpunan T akhir: {5, 10, 30} atau ditambah 60 (dengan stride)? | Bergantung pada RAM dan hasil T = 5 dan T = 30 |
| 5 | Berapa seed untuk seluruh sweep: 3 atau lebih? | Dengan sd HR@1 ≈ 0,10 di `leave_event_out`, 3 seed tidak cukup untuk selisih kecil |
| 6 | Skema mana yang dipakai untuk perbandingan fusion nanti? | Usulan: `within_event` sebagai utama |

Tiga tingkat protokol yang pernah diusulkan:

- **A:** protokol acak dari kode asli (hanya diagnostik batas atas).
- **B:** pembagian waktu 60/40 per periode (mirip `within_event`).
- **C:** `leave_event_out` (baseline untuk perbandingan fusion).

---

## 9. Masalah terbuka lain yang tercatat

1. **Slide 11 PPT lawan kode.** Slide itu menyebut empat kandidat fusion (F1–F4, termasuk Cross-Attention), sedangkan kode punya lima (`concat_glu`, `concat_fc`, `sum`, `attn`, `lmf`) dan Cross-Attention belum ada di kode.
2. **Ablasi modalitas** (pola Tabel IV paper: tanpa log/metrik/trace/graf) belum dilatih ulang. Paper TT melaporkan HR@1 menurun ke 0,926 (tanpa log), 0,776 (tanpa metrik), 0,785 (tanpa trace), 0,803 (tanpa graf). Diagnosis yang lebih awal pada run lama menunjukkan modalitas log tidak berpengaruh saat inferensi.
3. **Normalisasi per run** (z-score) adalah faktor pengganggu yang diketahui. Ablasi terkontrol belum dilakukan.
4. **Epoch.** Epoch terpilih sering yang terakhir; 15 epoch mungkin terlalu pendek.
5. **Portabilitas.** `peak_rss_mb` di `main.py` memakai `ru_maxrss/1024` (benar untuk Linux, salah untuk macOS), dan `run_train.sh` memakai `systemd-inhibit` (Linux saja). Bila training dipindah ke MacBook, kedua hal ini perlu disesuaikan, dan hasil dari platform berbeda tidak boleh dicampur dalam satu tabel.

---

## 10. Hasil T = 5 (skema `within_event`, 3 seed)

### 10.1 Pengaturan dan data

Semua pengaturan sama dengan baseline T = 10 (bagian 5.3); hanya T yang berubah. Data: `work/chunks/A1_T5/within_event`, `chunk_lenth = 5`.

| Bagian | T = 5 | T = 10 |
|---|---|---|
| Train | 40.930 (gangguan 24.868; normal 16.062) | 40.510 (24.823; 15.687) |
| Val | 7.910 (gangguan 5.489; normal 2.421) | 7.490 (5.084; 2.406) |
| Test | 32.610 (gangguan 17.990; normal 14.620) | 32.190 (17.990; 14.200) |
| Porsi normal di Test | 44,8% | 44,1% |
| Jendela dibuang (purge) | 960 | 2.160 |

Run:

| Seed | Hash | Epoch terpilih (`combo`) | Lama |
|---|---|---|---|
| 42 | `ee187163` | 9 | 10 mnt 04 dtk |
| 7 | `8b0b0528` | 4 | 9 mnt 40 dtk |
| 123 | `b8c0ba13` | 9 | 10 mnt 10 dtk |

Efisiensi: 65.400 parameter (T = 10: 66.050); 32 detik per epoch (T = 10: 51); ±0,18 ms per jendela (T = 10: 0,27); RAM puncak 2.132 MB (T = 10: 2.752 MB).

### 10.2 Per seed (Test, std, epoch terpilih)

| Metrik | Seed 42 | Seed 7 | Seed 123 |
|---|---|---|---|
| F1 | 0,708 | 0,742 | 0,779 |
| Recall | 0,946 | 0,979 | 0,903 |
| Precision | 0,566 | 0,598 | 0,685 |
| HR@1 | 0,809 | 0,801 | 0,787 |
| HR@3 | 0,882 | 0,906 | 0,845 |
| HR@5 | 0,908 | 0,924 | 0,872 |
| NDCG@3 | 0,852 | 0,863 | 0,822 |
| NDCG@5 | 0,862 | 0,871 | 0,833 |

### 10.3 Rata-rata ± sd, dibandingkan dengan T = 10

sd memakai pembagi n−1. Selang kepercayaan (SK) selisih memakai galat baku Welch dan t dengan 2 derajat kebebasan (4,303), yaitu pilihan konservatif. "|selisih|/galat" di bawah 2 kira-kira berarti selisih belum bisa dibedakan dari variasi antar seed.

| Metrik (std) | T = 5 (n = 3) | T = 10 (n = 3) | Selisih (5 − 10) | SK 95% selisih | \|selisih\| / galat |
|---|---|---|---|---|---|
| F1 | 0,743 ± 0,036 | 0,767 ± 0,017 | −0,024 | −0,121 s.d. +0,073 | 1,06 |
| Recall | 0,943 ± 0,038 | 0,923 ± 0,037 | +0,019 | −0,112 s.d. +0,151 | 0,63 |
| Precision | 0,616 ± 0,062 | 0,658 ± 0,045 | −0,042 | −0,231 s.d. +0,148 | 0,95 |
| HR@1 | 0,799 ± 0,011 | 0,822 ± 0,031 | −0,023 | −0,105 s.d. +0,059 | 1,19 |
| HR@3 | 0,878 ± 0,031 | 0,883 ± 0,024 | −0,005 | −0,103 s.d. +0,092 | 0,23 |
| HR@5 | 0,901 ± 0,027 | 0,896 ± 0,027 | +0,005 | −0,088 s.d. +0,098 | 0,25 |
| NDCG@3 | 0,846 ± 0,022 | 0,858 ± 0,027 | −0,012 | −0,097 s.d. +0,073 | 0,62 |
| NDCG@5 | 0,855 ± 0,020 | 0,863 ± 0,027 | −0,008 | −0,091 s.d. +0,075 | 0,42 |

Dibandingkan paper (F1 0,989; HR@1 0,990), T = 5 juga jauh di bawahnya, sama seperti T = 10.

Metrik asli kode, rata-rata ± sd (T = 5): F1 0,777 ± 0,055; HR@1 0,667 ± 0,094; HR@3 0,734 ± 0,113; HR@5 0,753 ± 0,113.

### 10.4 Alarm palsu (turunan, bukan dicatat kode)

Dihitung seperti di laporan seed, dari Recall, Precision, dan jumlah jendela, pada epoch terpilih.

| | Seed 42 | Seed 7 | Seed 123 | Rata-rata ± sd |
|---|---|---|---|---|
| T = 5, Val | 0,18 | 0,28 | 0,04 | 0,17 ± 0,13 |
| T = 5, **Test** | 0,89 | 0,81 | 0,51 | **0,74 ± 0,20** |
| T = 10, Test (dari laporan seed) | 0,46 | 0,70 | 0,69 | 0,62 ± 0,14 |

- Pada T = 5, ±74% jendela normal di Test diberi alarm, dibanding ±62% pada T = 10. Selisihnya kecil terhadap sd yang besar (0,20 dan 0,14), jadi tidak dapat disimpulkan berbeda.
- **Val tetap jauh lebih optimistis daripada Test** (alarm palsu 0,17 vs 0,74), sama dengan temuan di baseline T = 10.

### 10.5 Pemilihan epoch

- `combo` memilih epoch 9, 4, dan 9. Epoch 14 tidak pernah dipilih pada T = 5 (di T = 10: 14, 14, 9).
- Seed 7: Val `combo` turun dari 0,924 (epoch 4) ke 0,918 (epoch 9) dan 0,896 (epoch 14), padahal Precision Val naik hampir sempurna (0,887 → 0,995 → 0,994; alarm palsu Val turun ke ≈1%). Penurunan `combo` berasal dari Recall dan HR@1 Val yang turun. Karena Test tidak dihitung di epoch 9 dan 14, **tidak diketahui** apakah Test ikut membaik pada alarm palsunya.
- Seed 42 dan 123: pada epoch 4 yang tidak terpilih, Test HR@1 lebih rendah (0,703 dan 0,766) daripada epoch terpilih (0,809 dan 0,787). Pada dua seed ini pemilihan oleh Val tepat untuk lokalisasi.

### 10.6 Kesimpulan dan koreksi

1. **T = 5 dan T = 10 tidak dapat dibedakan dengan 3 seed.** Tidak ada metrik dengan |selisih|/galat di atas 1,2, dan semua SK selisih mencakup nol. Selisih dengan SK sempit sekalipun (±0,1) tidak dapat dikesampingkan.
2. **Arah selisih konsisten tetapi kecil:** F1 −0,024, Precision −0,042, HR@1 −0,023, Recall +0,019. Semuanya dalam rentang variasi antar seed.
3. **Koreksi atas pembacaan awal.** Setelah seed 42 saja, selisih Precision tampak −0,144 terhadap T = 10 seed 42, dan alarm palsu 0,89 tampak jauh lebih tinggi. Setelah 3 seed, selisih rata-rata Precision hanya −0,042 dan rentang Precision T = 5 (0,566–0,685) bertumpang tindih dengan T = 10 (0,632–0,710). Pembacaan satu seed itu tidak bertahan.
4. **Variasi antar seed sedikit berbeda:** sd Precision dan F1 pada T = 5 lebih besar (0,062 dan 0,036 vs 0,045 dan 0,017), sedangkan sd HR@1 lebih kecil (0,011 vs 0,031). Dengan 3 seed, perbedaan sd ini pun tidak pasti.
5. **T = 5 jauh lebih murah** tanpa kehilangan kualitas yang terlihat: waktu per epoch turun ±37% dan RAM ±23%. Ini satu-satunya perbedaan yang jelas.
6. **Hubungan dengan hipotesis trace (bagian 4).** T = 5 hanya memuat satu lonjakan trace pada ±10% jendela, setengah dari T = 10 (±18%), tetapi tidak ada penurunan yang jelas. Satu kemungkinan, yang masih perlu diuji dan bukan kesimpulan: pada T = 10 pun modalitas trace belum menjadi penentu hasil. Untuk menjawabnya perlu ablasi modalitas (bagian 9) dan hasil T = 30 dan T = 60.
7. **Keterbatasan:** hanya 3 seed dan satu skema; kriteria seleksi dan jadwal evaluasi sama dengan baseline T = 10; pembagian data tetap, dengan jumlah jendela dibuang yang berbeda (960 vs 2.160). Dugaan penyebab selisih kecil yang ada tidak diselidiki.
