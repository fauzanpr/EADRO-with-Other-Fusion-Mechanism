# Penjelasan Pekerjaan: Menyiapkan Reproduksi EADRO di Data Train Ticket

Dokumen ini menjelaskan, dengan bahasa sederhana, **apa yang sudah dikerjakan, kenapa dikerjakan, dan bagaimana kita tahu hasilnya benar**. Tidak perlu latar belakang machine learning. Istilah teknis dijelaskan saat pertama muncul, dan ada daftar istilah di Bagian 2.

Tanggal pengerjaan: 26 Oktober 2026. Status: **data dan kode sudah siap latih; training baseline penuh belum dijalankan.**

---

## 1. Gambaran besar

### Tujuan proyek
Tugas besar Anda: **mereplikasi EADRO** (makalah ICSE 2023) pada data sistem Train Ticket, lalu **mengganti dan membandingkan "mekanisme fusion"-nya** (cara model menggabungkan tiga jenis data) dari sisi akurasi dan efisiensi.

### Apa itu EADRO, dengan analogi
Bayangkan sebuah rumah sakit dengan **27 pasien**. Pasien itu adalah 27 *service* (layanan/komponen) pada aplikasi Train Ticket. Setiap 10 detik, seorang dokter memeriksa semua pasien memakai **tiga alat periksa**:

| Alat periksa | Istilah teknis | Isinya |
|---|---|---|
| Termometer dan tensimeter | **Metrics** | Angka pemakaian: CPU, memori, jaringan, dll. (7 angka per service) |
| Catatan perjalanan pasien | **Traces** | Berapa lama sebuah service menunggu jawaban service lain (latensi) |
| Buku harian pasien | **Logs** | Catatan teks yang ditulis tiap service |

Dokter (model EADRO) harus menjawab **dua pertanyaan sekaligus** untuk tiap 10 detik:
1. **Deteksi:** adakah yang sakit (ada gangguan) atau semua sehat?
2. **Lokalisasi:** kalau ada, **pasien nomor berapa** (service mana) yang menjadi biang masalahnya?

### Di mana "fusion" berada
Setiap alat periksa dibaca oleh "asisten" sendiri (disebut *encoder*), yang meringkasnya jadi 64 angka per service. Lalu tiga ringkasan itu **digabung** menjadi satu. Di EADRO asli, cara menggabungnya: *sambung ketiganya, lewatkan satu lapisan Linear, lalu satu "gerbang" bernama GLU*. Bagian penggabungan inilah **fusion**, dan inilah yang akan Anda ubah dan bandingkan. Makalah EADRO tidak pernah membandingkan cara penggabungan lain, itulah celah penelitian Anda.

Setelah digabung, hasilnya dipadukan dengan peta hubungan antar service (**graf**, memakai GATv2), lalu keluar dua jawaban di atas.

---

## 2. Daftar istilah singkat

| Istilah | Arti sederhana |
|---|---|
| **Service** / **node** | Satu komponen aplikasi. Ada 27 di Train Ticket. |
| **Fault** (gangguan) | Kerusakan yang sengaja disuntikkan untuk percobaan: `cpu_load` (CPU dibebani), `network_delay` (jaringan diperlambat), `network_loss` (paket jaringan hilang). |
| **Culprit** (biang) | Service tempat fault disuntikkan. Ini "jawaban benar" untuk lokalisasi. Bila tidak ada fault, culprit = −1. |
| **Run** | Satu sesi percobaan yang direkam utuh. |
| **Jendela (window)** | Potongan data 10 detik yang menjadi satu contoh untuk model. Digeser 1 detik tiap kali, jadi jendela bertetangga berbagi 9 dari 10 detik. |
| **Chunk** | Satu jendela yang sudah dirapikan jadi bentuk siap-masuk-model. |
| **Train / Val / Test** | Tiga tumpukan data. **Train**: model belajar dari sini. **Val** (validasi): dipakai memilih kapan berhenti belajar. **Test**: ujian akhir, tidak boleh ikut memengaruhi pilihan apa pun. |
| **Epoch** | Satu putaran model membaca seluruh data train. |
| **Kebocoran data (leakage)** | Ujian yang soalnya sudah pernah dilihat saat belajar, sehingga nilai terlihat bagus padahal menipu. |
| **F1, Recall, Precision** | Ukuran seberapa benar deteksi "ada gangguan / tidak". Makin dekat 1 makin baik. |
| **HR@1** | *Hit Rate* peringkat 1: seberapa sering service biang asli ditebak di **urutan pertama**. HR@3, HR@5 = masuk 3 atau 5 teratas. |
| **NDCG** | Mirip HR, tetapi memberi nilai lebih bila tebakan benar berada di peringkat lebih atas. |
| **Seed** | Angka awal pengacak. Seed berbeda memberi hasil sedikit berbeda, jadi eksperimen sebaiknya diulang dengan beberapa seed. |

---

## 3. Data yang kita punya

- **9 run dengan fault.** Tiap run ±6.461 detik, berisi 9 kali penyuntikan fault. Total **81 kejadian fault** (27 service × 3 jenis fault). Makalah menyebut 162, jadi data kita separuh dari makalah.
- **3 run tanpa fault** (kondisi normal), masing-masing ±8.107 detik. Totalnya ±6,75 jam, hampir sama dengan "7 jam data normal" di makalah.
- Total **12 run**, menghasilkan **82.350 jendela**, dengan **59,9% di antaranya jendela bergangguan**.

Satu hal penting yang harus Anda pahami: 82 ribu jendela itu **bukan 82 ribu kejadian independen**. Karena digeser tiap 1 detik, jendela bertetangga hampir kembar. Kejadian yang benar-benar berbeda hanya **81**. Inilah alasan kenapa cara membagi data (Bagian 5.4) sangat menentukan kejujuran hasil.

---

## 4. Penilaian awal: bisakah kode EADRO langsung dijalankan?

Saya membaca seluruh kode di folder `Eadro/` lebih dulu, tanpa menjalankannya. Kesimpulannya: **tidak bisa langsung jalan.** Ada dua masalah besar.

**(a) Kode model punya bug.** Beberapa contoh: ada variabel yang dipakai tetapi tidak pernah didefinisikan (`trace_dropout`, `metric_dropout`), nama atribut tidak konsisten (`locator` vs `localizer`), ada `numpy` yang lupa di-import (akan crash di epoch ke-9), dan satu argumen (`edges`) tidak diteruskan.

**(b) Bagian pengolah data mentah tidak ada.** Repositori hanya berisi kode dari data yang *sudah diolah* (folder `parsed_data`) menuju model. Kode dari **data mentah** (file spans, logs, CSV) menuju `parsed_data` **tidak disertakan**, dan data di Zenodo juga hanya berisi data mentah. Jadi bagian ini harus kita bangun sendiri.

Akibatnya, proyek ini bukan sekadar "clone lalu jalankan", melainkan **membangun ulang jalur data dan memperbaiki model**. Karena itu juga, angka di makalah (F1 0,988, HR@1 0,982) **tidak boleh dijadikan target persis**.

---

## 5. Apa yang saya kerjakan, urut

### 5.1 Memperbaiki model, lalu mengujinya dengan data buatan (smoke test)

**Apa:** memperbaiki bug-bug di atas pada `Eadro/codes/` (file `main.py`, `base.py`, `model.py`, dan `single_process.py`).

**Kenapa pakai data buatan:** sebelum mengolah data asli yang rumit, saya ingin memastikan *mesin modelnya* sendiri sehat. Saya membuat data sintetis (angka buatan dengan pola yang sengaja ditanam per service), lalu menjalankan `main.py` yang asli. Bila model sehat, ia harus mampu menemukan pola itu.

**Hasilnya:** model berjalan dari awal sampai akhir dan belajar (loss turun, HR@1 jauh di atas tebakan acak). Hasilnya juga **deterministik**: dijalankan ulang, angkanya sama.

**Satu kesalahan saya di tahap ini:** pada percobaan pertama, pola buatan saya sama untuk semua service, sehingga model tidak mungkin membedakannya dan HR@1 mendekati tebakan acak. Itu salah rancangan data uji saya, bukan bug model. Saya perbaiki dengan pola khusus per service.

**Keputusan teknis:** bagian trace pada model menerima 1 kanal (satu deret angka latensi). Itu sesuai makalah ("univariate latency series"), jadi yang saya sesuaikan adalah bentuk data, bukan modelnya.

File: `smoke_test/make_smoke_chunks.py`, `smoke_test/run_smoke_test.sh`.

### 5.2 Membangun jalur data mentah → siap latih

Ini bagian terbesar. Saya membuatnya bertahap, satu sumber data per tahap, dan **setiap tahap diverifikasi dengan fungsi asli EADRO** supaya hasilnya setara dengan yang dimaksud penulis.

#### a) Records dan Metrics
- **Records**: daftar "kapan fault terjadi, di service mana, jenis apa" untuk tiap run. Dipakai membuat label (culprit) tiap jendela.
- **Metrics**: 27 file CSV per run (satu per service), 7 kolom angka. Disalin apa adanya dan dicek keutuhannya dengan checksum (sidik jari file). Datanya bersih: tidak ada celah waktu, duplikat, maupun NaN.
- Verifikasi memakai fungsi asli `get_basic` dan `deal_metrics`. Setiap service punya 1.823–1.830 jendela bergangguan, jadi cukup merata.

#### b) Traces (latensi antar service)
- **Aturan pengaitan:** bila service A memanggil service B dan menunggu 50 ms, angka itu dicatat sebagai latensi **milik B** (penerima panggilan). Ini mengikuti makalah ("latensi pemanggilan untuk tiap callee").
- Data mentah punya duplikat sekitar 4 kali lipat; saya buang duplikatnya.
- **Temuan penting soal waktu:** jam pada file spans dan logs **selisih 8 jam** dari jam label/metrics. Saya buktikan: hanya dengan menggeser +8 jam, span jatuh di dalam rentang run. Ini terbukti pada semua 12 run.
- **Bukti bahwa trace bermakna:** saat `network_delay` disuntikkan, latensi naik 1,7 sampai 4,4 kali lipat. Saat `network_loss`, naik ratusan kali lipat. Saat `cpu_load`, latensi tidak naik. Ini persis klaim makalah, jadi pengaitan kita masuk akal.
- **Keterbatasan:** hanya **9 dari 27 service** yang punya data trace, dan di 9 itu pun hanya ±15% jendela berisi minimal satu catatan. Ini sifat dari data yang direkam (14 service memang tidak muncul di spans), bukan kesalahan kita.

#### c) Logs (catatan teks)
Log itu teks bebas, sedangkan model butuh angka. Dua langkah:
1. **Drain (pengelompokan pola teks).** Baris seperti `User 123 login ok` dan `User 456 login ok` dianggap pola yang sama. Hasilnya **59 pola (template)** dari 124.571 baris. Sekitar 40% baris hanya satu pola: log "Span reported" milik Jaeger (alat pelacak), bukan log aplikasi.
2. **Hawkes (mengubah pola menjadi angka).** Untuk tiap jendela dan service, dihitung fitur numerik yang menggambarkan seberapa sering tiap pola muncul. Dihitung memakai pustaka `tick`, yang hanya bisa jalan di Python 3.8, jadi saya membuat lingkungan Python 3.8 khusus (`work/envs/preproc38`).

**Bug penting di kode asli EADRO (sudah saya perbaiki):** pada perhitungan Hawkes, "panjang jendela" diberi nilai *cap waktu absolut* (angka miliaran) alih-alih 10 detik. Akibatnya semua fitur log bernilai sama (6,06e-10), alias **seluruh data log tidak membawa informasi apa pun**. Perbaikannya satu baris: pakai `e+1-s` (panjang jendela), bukan `e+1`. Sebelum dan sesudah perbaikan sudah saya bandingkan.

**Keterbatasan fitur log (jujur):** setelah diperbaiki, nilai Hawkes cenderung "jenuh" di sekitar 0,1. Pola yang tidak muncul sama sekali dan pola yang muncul 1 sampai 10 kali hampir tidak dibedakan (median 0,1000 vs 0,1035). Praktisnya, fitur log lebih banyak mengatakan "service ini punya log di jendela ini atau tidak", bukan "seberapa banyak". Hanya **13 dari 27 service** yang punya log. Karena saya sengaja setia pada kode asli, ini saya laporkan apa adanya, bukan saya perhalus. Konsekuensinya, kontribusi log pada hasil akhir kemungkinan kecil.

#### d) Cache per run
Menghitung Hawkes memakan waktu (±70 ms per jendela, sekitar 1 jam total di 8 core). Karena itu hasil tiap run disimpan (`traces.pkl`, `metrics.pkl`, `logs.pkl`) supaya tidak dihitung ulang. Sudah diperiksa independen: aktivitas log di fitur **cocok 100%** dengan baris log di CSV (0 ketidakcocokan).

### 5.3 Kenapa saya tidak memakai "fork" EADRO milik orang lain
Anda sempat menemukan fork `FeiGSSS/Eadro`. Saya periksa, dan keputusan akhirnya (Anda yang menyetujui) adalah **tidak memakainya**. Alasannya:
- Di fork itu, **0 dari 83.567 baris log** jatuh di dalam jendela pengamatan (jamnya tidak digeser dengan benar). Artinya modalitas log praktis kosong.
- Dua kesalahan lain di fork saling menutupi, sehingga masalahnya tak terlihat.
- Bug Hawkes di atas tidak diperbaiki.
- Pembagian data acak yang bocor, dan hanya 9 run (tanpa data normal tambahan).

Pipeline kita lebih bisa dipertanggungjawabkan karena tiap keputusan punya bukti.

### 5.4 Membagi data train/val/test dengan benar (bagian paling halus)

**Masalah di kode asli:** `align.py` membagi jendela secara **acak**. Karena jendela bertetangga hampir kembar (berbagi 9 dari 10 detik), jendela di Train dan Test akan saling "mengintip". Ibarat ujian yang soalnya hampir sama persis dengan latihan, nilainya jadi terlalu bagus dan menyesatkan. Itu yang disebut **kebocoran data**. Kode asli juga memilih epoch terbaik memakai Test, yang juga membuat angka terlalu optimistis.

**Solusi saya:** pembagian dilakukan **berdasarkan waktu, per detik**:
- Setiap detik diberi label Train/Val/Test. Sebuah jendela hanya dipakai bila **semua 10 detiknya** berlabel sama. Jendela yang melintasi batas dibuang (disebut *purge*).
- Hasilnya, **tidak ada satu detik pun yang dipakai bersama** oleh dua tumpukan. Ini sudah saya buktikan dengan program pemeriksa terpisah: **0 detik bersama** di kedua skema.

Saya membuat **dua skema pembagian**:

| | `within_event` | `leave_event_out` |
|---|---|---|
| Ide | Tiap kejadian fault dipotong menurut waktu: 50% awal Train, 10% Val, 40% akhir Test | Untuk tiap service, **satu jenis fault** disisihkan seluruhnya untuk Test (model tidak pernah melihatnya saat belajar), plus satu run tanpa fault |
| Pertanyaan yang dijawab | Bisakah model mengenali fault yang pola serupanya sudah pernah dilihat? (paling dekat dengan teks makalah) | Bisakah model menggeneralisasi ke **jenis fault yang belum pernah dilihat** untuk service itu? (lebih sulit dan lebih jujur) |
| Train / Val / Test | 40.510 / 7.490 / 32.190 | 46.160 / 7.695 / 27.352 |
| Jendela dibuang (purge) | 2.160 | 1.143 |

Di kedua skema, **semua 27 service punya contoh di Train, Val, dan Test**, dan proporsi jendela bergangguan seimbang (±56–65%).

File: `pipeline/build_chunks_split.py`. Hasil di `work/chunks/A1/within_event/` dan `work/chunks/A1/leave_event_out/`.

**Catatan (ditemukan setelah training pertama, lihat Bagian 13):** pada skema `within_event`, Val ternyata tidak memuat jendela normal dari run berfault, sehingga Val tidak mewakili Test dengan baik. Ini kelemahan rancangan skema tersebut.

### 5.5 Memperbaiki cara model dilatih (`main.py`, `base.py`, `utils.py`)

Dua perubahan, sesuai yang Anda setujui:

**Perubahan 1: pilih epoch dengan Val, bukan Test.**
Setiap beberapa epoch, model diuji pada **Val**. Epoch dengan nilai Val terbaik dipilih, dan **Test baru dihitung hanya pada epoch yang terpilih**. Dengan begitu Test benar-benar "ujian akhir", tidak ikut menentukan apa pun. Saya juga memperbaiki crash kalau jumlah epoch kurang dari 10.

**Perubahan 2: hemat memori.**
Kode asli membuat satu objek graf per contoh dan menyimpan semuanya di memori. Untuk 80 ribu contoh, itu butuh sekitar 8 GB, padahal RAM bebas Anda sekitar 8,8 GB. Sekarang fitur disimpan rapat dalam tensor, dan graf dirakit hanya saat satu batch dibutuhkan. Saya **buktikan hasilnya identik** dengan cara lama (struktur graf, fitur, dan label sama persis pada contoh uji). Pemakaian memori puncak turun menjadi **2,9 GB**.

### 5.6 Uji coba pada data asli (1 epoch saja)

Saya menjalankan 1 epoch pada data `within_event` yang asli, hanya untuk mengukur kebutuhan sumber daya dan memastikan alurnya jalan:

| Hal | Hasil |
|---|---|
| Waktu latih | 76 detik per epoch |
| Waktu evaluasi | Val 18 detik, Test 70 detik |
| Memori puncak | 2,9 GB |
| Val setelah 1 epoch | HR@1 = 0,291; F1 = 0,931 |

Tebakan acak untuk HR@1 adalah 1/27 ≈ 0,037, jadi model sudah belajar sesuatu dari data kita sejak epoch pertama. **Ini bukan hasil baseline.** Angka ini baru 1 epoch, hanya untuk membuktikan alurnya hidup. Pesan "Unable to convergence" yang muncul hanya karena aturan kode asli (epoch terbaik harus > 5) dan wajar untuk 1 epoch.

---

## 6. Temuan penting soal cara kode asli menghitung F1 dan HR@1

Saat menulis dokumen ini saya membaca ulang fungsi `evaluate()` di `base.py` dan menemukan dua kebiasaan kode asli yang harus Anda ketahui karena memengaruhi cara membaca semua angka:

1. **"F1" bukan F1 biasa untuk kelas gangguan.** Di kode, jendela *normal* yang ditebak normal juga dihitung sebagai "benar positif (TP)". Jadi "F1" di sini mengukur ketepatan membedakan normal vs bergangguan secara umum, dan cenderung terlihat lebih tinggi dari F1 baku untuk kelas gangguan saja.
2. **Penyebut HR@1 ikut menghitung jendela normal yang tertebak benar.** HR@k dibagi `TP + FN`, dan karena jendela normal yang benar ikut masuk TP, penyebutnya lebih besar dari jumlah jendela bergangguan. Akibatnya HR@k yang tercetak **lebih rendah** dari "persentase jendela bergangguan yang biangnya tertebak benar".

Contoh perhitungan dari log 1-epoch tadi (Val: 5.084 jendela bergangguan, 2.406 normal). Dari Recall dan Precision yang tercetak saya hitung mundur (perkiraan, karena angkanya dibulatkan): ±2.137 jendela normal tertebak normal, dan HR@1 tercetak 0,291 setara ±2.100 tebakan biang yang tepat. Bila dibagi **jumlah jendela bergangguan** (bukan penyebut kode asli), HR@1 menjadi sekitar **0,41**, bukan 0,29.

**Sudah ditangani (setelah Anda setuju).** Angka versi kode asli **tidak diubah** dan tetap dicetak (supaya sebanding dengan makalah). Di sampingnya sekarang ikut dicetak versi baku, ditandai akhiran `(std)`:

| Kunci | Arti |
|---|---|
| `F1`, `Rec`, `Pre`, `HR@k`, `ndcg@k` | Versi kode asli (tidak berubah) |
| `F1(std)`, `Rec(std)`, `Pre(std)` | Deteksi hanya untuk **kelas gangguan**: benar positif = jendela bergangguan yang terdeteksi; jendela normal tidak dihitung sebagai positif |
| `HR@k(std)`, `ndcg@k(std)` | Dibagi **jumlah jendela bergangguan**. Gangguan yang terlewat (ditebak normal) dihitung sebagai gagal |

Perubahan ini hanya menambah angka, tidak memengaruhi cara model belajar. Pemilihan epoch tetap memakai `HR@1` versi asli pada Val, supaya perilaku training sama dengan kode aslinya.

Cara saya memastikannya benar: model dilatih sebentar, lalu semua metrik `(std)` dihitung ulang secara terpisah dari prediksi mentah. Hasilnya cocok sampai ketelitian 1e-9. Hubungan antara dua versi juga terpenuhi: `HR@k(asli) × (TP+FN) = HR@k(std) × jumlah_jendela_bergangguan`.

Di laporan, pakai kedua angka secara konsisten untuk semua varian fusion, jadi perbandingan antar fusion tetap adil.

---

## 7. Ringkasan: perubahan pada kode asli

| File | Perubahan | Alasan |
|---|---|---|
| `Eadro/codes/main.py` | Teruskan `edges`; muat Val; dataset dengan graf per batch | Bug, memori |
| `Eadro/codes/base.py` | `import numpy`; pilih epoch via Val; Test hanya di epoch terpilih; cadangan bila epoch < 10; metrik tambahan `(std)` di `evaluate()` | Bug, kebocoran, pelaporan |
| `Eadro/codes/utils.py` | Muat tiga file (train, val, test) | Mendukung Val |
| `Eadro/codes/model.py` | Hapus argumen `dropout` yang tak didukung; perbaiki nama atribut | Bug |
| `Eadro/codes/preprocess/single_process.py` | Trace jadi 1 kanal; perbaiki bug horizon Hawkes (`e+1-s`) | Bug, sesuai makalah |
| `Eadro/codes/preprocess/align.py` | Komentar ukuran saja | Dokumentasi |

Semua skrip baru ada di folder `pipeline/` dan `smoke_test/`. Data mentah asli (`TT Dataset/`) **tidak diubah**; semua hasil olahan ada di folder `work/`.

---

## 8. Hal yang perlu Anda sampaikan dengan jujur di laporan

1. Kode rilis EADRO tidak bisa dijalankan apa adanya, dan jalur data mentah tidak tersedia, sehingga ini adalah **re-implementasi** dengan perbaikan, bukan sekadar menjalankan ulang.
2. Data kita memuat 81 kejadian fault (makalah: 162), jadi angka tidak otomatis sebanding dengan makalah.
3. Trace hanya mencakup 9 dari 27 service dan log hanya 13 dari 27; sisanya kosong karena sifat data.
4. Fitur log (Hawkes) jenuh dan hanya sedikit informatif, meskipun bug horizon sudah diperbaiki.
5. Pembagian data dilakukan per waktu dengan *purge* untuk mencegah kebocoran, dan epoch dipilih dengan Val, bukan Test. Ini lebih ketat daripada kode asli, jadi angkanya wajar lebih rendah dari makalah.
6. F1 dan HR@k pada kode asli dihitung dengan cara khusus (Bagian 6); kita laporkan keduanya.

---

## 9. Keputusan yang masih terbuka

- **Normalisasi data metrics:** kode asli menormalkan **per run**. Run tanpa fault dan run berfault jadi berskala berbeda, karena fault jaringan menghasilkan nilai ekstrem. Belum diputuskan apakah dibiarkan (setia kode asli) atau diubah, mis. memakai statistik dari data normal saja.
- **Panjang jendela dan ukuran slot trace:** kita memakai pengaturan EADRO (jendela 10 detik, slot 1 detik). Notebook EDA Anda memakai 60 detik dan 5 detik. Usul saya: setia dulu, lalu jadikan ablasi.
- **Cadangan trace dari sisi server:** menambah 4 service (13 dari 27 bertrace). Opsional, belum dibuat.
- **Aturan label jendela bergangguan:** kita memakai ambang 1 detik (default kode); notebook EDA memakai ≥50%.

---

## 10. Langkah berikutnya

1. **Training baseline penuh** (50 epoch, ±1,1 jam per skema) pada `within_event`, lalu `leave_event_out`.
2. **Ulangi dengan 2–3 seed** supaya tahu seberapa besar variasi hasil. Selisih antar mekanisme fusion bisa lebih kecil dari variasi antar seed, jadi tanpa ini kesimpulan bisa menyesatkan.
3. (Sudah dikerjakan) HR@k dan F1 versi baku sudah ditambahkan di samping versi kode asli (Bagian 6).
4. Barulah membuat **varian fusion** (misal penjumlahan, atensi, gerbang lain) dan membandingkannya pada F1, HR@1, NDCG, jumlah parameter, waktu, dan memori.
5. Opsional: ablasi (tanpa log, tanpa trace, setelan T/slot lain) untuk menunjukkan peran tiap sumber data.

---

## 11. Cara menjalankan training sendiri

Semua perintah dijalankan dari folder proyek (`EADRO - APDM`). Lingkungan Python training sudah permanen di `work/envs/train312` (dibuat dari nol dan diuji). Bila suatu saat perlu dibuat ulang: `pipeline/setup_train_env.sh` (±2 menit, butuh internet).

**Satu perintah, satu training:**

```
pipeline/run_train.sh <skema> [seed] [epoch]
```

| Contoh | Maksudnya |
|---|---|
| `pipeline/run_train.sh within_event 42 1` | Uji cepat 1 epoch (±3 menit). Jalankan ini dulu untuk memastikan semuanya hidup. |
| `pipeline/run_train.sh within_event 42` | Training penuh: 50 epoch (±70–80 menit + evaluasi), seed 42. |
| `pipeline/run_train.sh leave_event_out 42` | Skema kedua (lebih sulit). |
| `nohup pipeline/run_train.sh within_event 42 > train_we42.out 2>&1 &` | Jalan di latar belakang, tidak mati walau terminal ditutup. |

**Memantau:** `tail -f work/result/<hash_id>/running.log` (nama folder `<hash_id>` tercetak di akhir log; tiap kombinasi parameter punya satu folder). Satu baris per epoch menampilkan *training loss* (harus cenderung turun) dan waktunya (±80 detik).

**Kapan muncul hasil:** evaluasi dilakukan setiap 10 epoch, yaitu pada epoch **9, 19, 29, 39, 49**. Tiap kali, baris `Val -- ...` muncul. Bila Val lebih baik dari sebelumnya, baris `Test -- ...` ikut dihitung dan model disimpan. Hasil akhir yang dipakai adalah baris `Test` dari epoch dengan Val terbaik.

**Cara membaca satu baris hasil:** angka tanpa akhiran = versi kode asli; angka berakhiran `(std)` = versi baku (Bagian 6). Untuk laporan, lihat terutama `HR@1`, `HR@1(std)`, `F1`, `F1(std)`, dan `ndcg@1`. Bacaan sehat: `HR@1(std)` jauh di atas 0,037 (tebakan acak untuk 27 service). Contoh 1 epoch: Val `HR@1(std)` = 0,41.

**Ringkasan semua run (teks):** `work/result/experiments.txt` (satu blok per run, berisi hasil Test dan epoch terbaik).

**Tabel dan gambar.** Kode asli EADRO hanya menulis teks, jadi saya membuat pembaca hasil sendiri (`pipeline/baca_hasil.py`). Ada dua cara memakainya, dan keduanya menghasilkan isi yang sama:

| Cara | Perintah / file | Keluaran |
|---|---|---|
| Notebook (disarankan untuk dilihat dan dipelajari) | Buka `Hasil_Training.ipynb`, pilih kernel `work/envs/train312/bin/python`, *Run All* | Tabel dan gambar langsung tampil, dengan penjelasan cara membacanya |
| Terminal | `work/envs/train312/bin/python pipeline/baca_hasil.py` | Mencetak tabel dan menyimpan file |

File yang dihasilkan (selalu ditulis ulang dari log, jadi aman dijalankan berulang, juga saat training masih berjalan):
- `work/result/ringkasan_hasil.csv`: satu baris per run (skema, seed, epoch terpilih, waktu latih, Val dan Test). Bisa dibuka di Excel/LibreOffice.
- `work/result/gambar/kurva_loss.png`: training loss per epoch. Yang sehat: cenderung turun.
- `work/result/gambar/val_hr1_std.png`: HR@1(std) pada Val di tiap evaluasi; titik besar = epoch terpilih.
- `work/result/gambar/hasil_akhir_<run>.png`: metrik Test pada epoch terpilih, versi baku (biru) vs versi kode asli (abu-abu).
- Bila ada beberapa seed untuk satu skema, tabel kedua menampilkan **rata-rata ± simpangan baku antar seed**. Run uji cepat (kurang dari 10 epoch) tidak ikut dihitung.

Alat ini sudah diuji pada run asli Anda (1 epoch) dan pada tiga run demo 30 epoch (data buatan, hanya untuk menguji tampilan; bukan hasil sungguhan).

**Aturan main supaya hasil bisa dibandingkan:**
- Satu run = satu kombinasi (skema, seed, parameter). Jangan menimpa folder hasil; biarkan skrip membuat folder baru.
- Bandingkan varian fusion hanya pada **skema yang sama dan seed yang sama**, dan ulangi beberapa seed (mis. 42, 7, 2024) untuk melihat variasi acak.
- Selama training berjalan, hindari pekerjaan berat lain: semua 8 core CPU terpakai.
- Jangan ubah isi `work/chunks/` (data hasil olahan) di tengah rangkaian eksperimen.

**Bila ingin memakai notebook:** pakai notebook untuk *membaca hasil*: `Hasil_Training.ipynb` (di folder proyek) sudah menyiapkan tabel dan gambarnya. Env yang sama berisi `ipykernel` dan `matplotlib`, jadi di VS Code/Jupyter pilih kernel `work/envs/train312/bin/python`. Untuk menjalankan training dari notebook, cukup satu sel `!pipeline/run_train.sh within_event 42 1`, tetapi run panjang tetap lebih aman lewat terminal.

---

## 12. Daftar file penting

| Lokasi | Isi |
|---|---|
| `Eadro/codes/` | Kode model EADRO yang sudah diperbaiki |
| `pipeline/common.py` | Pengaturan dan fungsi bersama |
| `pipeline/build_records_metrics.py` | Membuat label dan menyalin metrics |
| `pipeline/build_traces.py` | Membuat data trace |
| `pipeline/build_logs.py` | Mengelompokkan log dengan Drain |
| `pipeline/setup_preproc_env.sh` | Membuat lingkungan Python 3.8 untuk `tick` |
| `pipeline/build_run_caches.py` | Menghitung fitur tiap run (termasuk Hawkes) |
| `pipeline/build_chunks_split.py` | Merakit chunk dan membagi Train/Val/Test |
| `pipeline/verify_with_eadro.py`, `verify_caches.py` | Program pemeriksa independen |
| `smoke_test/` | Uji model dengan data buatan |
| `work/preprocess/parsed_data/A1/` | Data hasil olahan (records, metrics, traces, logs, template) |
| `work/chunks/A1/within_event/`, `.../leave_event_out/` | Data siap latih (Train/Val/Test) + `split_summary.json` |
| `pipeline/setup_train_env.sh`, `pipeline/run_train.sh` | Menyiapkan lingkungan training dan menjalankan satu training (Bagian 11) |
| `work/result/` | Hasil training (dibuat otomatis saat run pertama), plus `ringkasan_hasil.csv` dan folder `gambar/` |
| `pipeline/run_grid.sh` | Menjalankan banyak training berurutan (fusion × seed), Bagian 14 |
| `Hasil_Training.ipynb`, `pipeline/baca_hasil.py` | Menampilkan tabel dan gambar hasil training (Bagian 11) |

**Catatan lingkungan Python.** Ada dua lingkungan terpisah, keduanya permanen di folder proyek:
- `work/envs/preproc38` (Python 3.8 + `tick`): hanya untuk pengolahan data (Hawkes). Tidak perlu disentuh lagi kecuali data diolah ulang.
- `work/envs/train312` (Python 3.12 + PyTorch 2.2.1 CPU + DGL 2.1.0 + scikit-learn 1.5.2): untuk training dan membaca hasil.

---

## 13. Hasil baseline pertama dan diagnosisnya (update 27 Oktober)

### 13.1 Hasil run pertama (`within_event`, seed 42, 50 epoch, run `9df622b8`)
Epoch terpilih = **9** (evaluasi pertama). Pada epoch 9, hasil **Test**:

| | Versi baku (std) | Versi kode asli |
|---|---|---|
| HR@1 | 0,808 | 0,607 |
| HR@3 | 0,875 | 0,657 |
| HR@5 | 0,889 | 0,667 |
| F1 deteksi | 0,764 | 0,816 |

Tebakan acak untuk HR@1 hanya 0,037, jadi model jelas belajar. Setelah epoch 9, nilai Val datar (HR@1(std) 0,90–0,93) sementara *training loss* terus turun (0,12 menjadi 0,03). Artinya model mulai menghafal data latih, dan 50 epoch tidak diperlukan. Waktu latih sebenarnya sekitar 53 menit (laptop sempat tidur 3,3 jam di tengah, tanpa memengaruhi hasil).

Catatan: HR@k versi kode asli punya batas atas sekitar 0,74 pada Test (karena penyebutnya, lihat Bagian 6). Jadi angka versi baku lebih adil untuk dibaca. Angka ini **tidak boleh dibandingkan langsung** dengan angka makalah: data kita setengahnya, pembagiannya lebih ketat, dan definisi metriknya berbeda.

### 13.2 Kesenjangan deteksi antara Val dan Test
Pada deteksi, **presisi turun dari 0,94 (Val) ke 0,66 (Test)**. Saya menjalankan model pada semua jendela dan memecah *alarm palsu* (jendela normal yang ditandai bergangguan) per jenis jendela (`pipeline/diagnose_alarm.py`). Alarm palsu pada jendela normal: **Train 19%, Val 12%, Test 58%**. Ada dua sumber yang berbeda:

**Sumber A: jendela normal di antara dua gangguan (di run berfault).**
Alarm palsu sekitar 80%, dan **sama tingginya di data latih sendiri (82%)**. Jadi ini bukan masalah generalisasi: model tidak berhasil membedakan "celah" dari "gangguan" bahkan pada data yang dipelajarinya. Celah antar-gangguan hanya sekitar 100 detik, dan alarmnya tinggi pada semua jarak dari gangguan (1 sampai 120 detik). Penyebabnya belum diketahui: bisa jadi efek sisa gangguan yang belum pulih, atau batas waktu label yang tidak pas dengan efek sebenarnya.

**Sumber B: jendela normal di run tanpa fault.**
Alarm palsu naik makin jauh dari bagian yang dipelajari model: 0,5% di Train, 12% di Val, 48% di Test. Per run (Test): 6%, 55%, dan 82%. Cek kasar tidak menemukan perubahan skala rata-rata pada metrics, jadi dugaan "perbedaan skala antar-run" belum terbukti. Pergeseran di kanal/service tertentu atau di fitur trace dan log belum diperiksa.

**Akibatnya pada Val.** Seluruh jendela normal di Val berasal dari run tanpa fault. Tidak ada satu pun jendela jenis Sumber A di Val. Karena itu Val tampak bagus padahal Test buruk, dan pemilihan epoch lewat Val tidak mencerminkan kondisi Test. Ini **kelemahan rancangan skema `within_event` yang saya buat**, dan harus disebut jujur di laporan.

**Jenis fault.** Deteksi dan lokalisasi paling lemah pada `network_loss` di Test (terdeteksi 77%, top-1 benar 71%), dibanding `cpu_load` (99,5% dan 92%) dan `network_delay` (94% dan 96%).

### 13.3 Dampak untuk proyek
- Lokalisasi (HR@1(std)) lebih bisa dipercaya daripada deteksi, karena hanya dihitung pada jendela bergangguan.
- Angka mutlak F1 dan Precision deteksi pada skema ini belum boleh dipakai untuk klaim "model bagus atau jelek". Untuk membandingkan varian fusion, selisih antar varian tetap bisa dibaca asal semuanya memakai pembagian yang sama.
- Skema `leave_event_out` kemungkinan lebih jujur, karena Val-nya memuat jendela normal pasca-gangguan dari run berfault.

### 13.4 Yang sedang dikerjakan
1. **Langkah 1:** menjalankan `leave_event_out` (seed 42, 30 epoch, ±40–45 menit) untuk memeriksa apakah Val di skema itu sudah mewakili Test.
2. **Langkah 2:** menyelidiki Sumber A dan B lebih dalam, dengan membandingkan nilai metrics mentah (bukan z-score) saat celah, saat gangguan, dan pada run tanpa fault, per service dan per kanal. Termasuk memeriksa apakah efek gangguan mulai sebelum, atau berlanjut sesudah, jendela yang berlabel gangguan.

Hasil keduanya akan ditambahkan ke bagian ini.

### 13.5 Hasil langkah 1: `leave_event_out` (run `d574273b`, seed 42, 30 epoch)
| | `within_event` | `leave_event_out` |
|---|---|---|
| Epoch terpilih | 9 | 9 |
| Test HR@1 (std) | 0,808 | **0,539** |
| Test HR@3 / HR@5 (std) | 0,875 / 0,889 | 0,666 / 0,731 |
| Test F1 / Presisi deteksi (std) | 0,764 / 0,663 | 0,780 / 0,703 |

- **Lokalisasi turun jauh (0,81 menjadi 0,54).** Ini wajar dan lebih jujur: pada skema ini, jenis fault tertentu untuk sebuah service sama sekali tidak ada di data latih.
- **Masalah alarm palsu tetap ada:** sekitar 55% jendela normal di Val dan sekitar 56% di Test ditandai bergangguan (perkiraan dari presisi dan recall yang dibulatkan). Prediksi saya terbukti: Val di skema ini sekarang mewakili Test. Artinya masalah alarm palsu **bukan sekadar akibat cara membagi data**.
- **Cara pemilihan epoch ikut bermasalah.** Kode asli memilih epoch dengan HR@1 versi asli pada Val. Karena penyebutnya ikut menghitung jendela normal yang benar, angka itu justru *turun* saat model mengurangi alarm palsu. Buktinya: dari epoch 9 ke epoch 29, presisi Val naik (0,44 ke 0,48) dan HR@1(std) Val naik (0,87 ke 0,90), tetapi HR@1 versi asli turun (0,435 ke 0,409), jadi epoch 9 yang dipertahankan. Sebaiknya epoch dipilih dengan metrik versi baku.

### 13.6 Hasil langkah 2: apa yang sebenarnya dipakai model untuk mendeteksi?
Fakta yang terukur (skrip `pipeline/diagnose_features.py` dan `pipeline/diagnose_ablation.py`):

1. **Efek gangguan CPU tepat dan cepat pulih.** Pada `cpu_load`, metrics service biang melonjak sekitar 30 kali ukuran variasi normalnya tepat selama jendela berlabel, lalu kembali normal segera setelah gangguan berakhir. Jadi dugaan "label meleset" atau "efek sisa" tidak terbukti untuk gangguan CPU. Semua gangguan berdurasi tepat 601 detik.
2. **Gangguan jaringan tidak terlihat di 7 metrics service biangnya.** Pada `network_delay` dan `network_loss`, metrics service biang hampir tidak bereaksi. Efeknya hanya mungkin tampak di trace (9 dari 27 service punya trace) atau di service lain.
3. **Jendela "celah" mirip jendela bergangguan, bukan jendela normal sungguhan.** Classifier non-linear pada ringkasan metrics hampir sempurna membedakan jendela normal di run tanpa fault dari jendela normal di run berfault (AUC 0,98), terutama lewat kanal CPU (AUC 0,996). Antara jendela celah dan jendela bergangguan, pembedaannya jauh lebih sulit (AUC 0,73). Log dan trace tidak membedakan (AUC 0,60).
4. **Percobaan "mematikan input" pada model yang sudah dilatih:**
   - Log dinolkan: tidak ada perubahan sama sekali. **Log tidak berkontribusi** pada deteksi.
   - Kanal memory dinolkan: **semua alarm hilang** (recall deteksi jatuh ke 0,2%). Kanal CPU dinolkan: recall turun dari 90% ke 60%, dan alarm palsu turun sekitar sepertiga.
   - Untuk gangguan jaringan, memory milik **service biang sendiri tidak berpengaruh**, tetapi memory **service lain** sangat menentukan (recall turun dari 94% ke 13%).
   - Catatan: menolkan input bukan data asli, jadi ini petunjuk arah, bukan bukti pasti.
5. **Alarm palsu di run tanpa fault muncul tiba-tiba**, bukan perlahan: nyaris 0–5% sampai sekitar detik ke-4.000, lalu melonjak di run 10 dan 11 (35–99%) sementara run 9 tetap rendah. Pemicunya belum ditemukan; tidak ada perubahan level besar pada metrics mentah.

**Tafsiran (belum terbukti):** deteksi pada baseline ini tampaknya banyak bersandar pada ciri tingkat-run (skala z-score per run dan kanal memory service lain), bukan pada efek gangguan di service biang. Itu menjelaskan mengapa jendela celah di run berfault hampir selalu dianggap bergangguan.

### 13.7 Dampak untuk tujuan proyek (perbandingan fusion)
- Model baseline ini secara praktis bersandar pada **metrics saja**; log tidak berperan dan trace hanya berperan sebagai masukan. Bila varian fusion dibandingkan di atas pengaturan ini, perbedaannya bisa lebih mencerminkan cara memproses ciri tingkat-run daripada kualitas penggabungan beberapa sumber data.
- Ini perlu disebut jujur sebagai keterbatasan, dan idealnya diperbaiki dulu (misalnya normalisasi yang tidak bergantung pada run) sebelum membandingkan fusion. Keputusan perbaikan ada di tangan Anda.

## 14. Persiapan perbandingan fusion (update 27 Oktober)
Sesuai kesepakatan ("jalan tengah"): perbandingan fusion tetap dilakukan di atas pengaturan data yang sekarang, dengan beberapa pengaman, dan keterbatasannya ditulis jelas di laporan.

### 14.1 Perubahan pada kode
- **Pemilihan epoch.** Sebelumnya epoch dipilih dengan HR@1 versi asli di Val, yang bias (lihat 13.5). Sekarang defaultnya `--select_metric combo`, yaitu rata-rata `F1(std)` dan `HR@1(std)` di Val. F1 menghukum alarm palsu, HR@1 menilai ketepatan menunjuk service biang. Kriteria lama tetap bisa dipakai dengan `--select_metric HR@1`.
- **Evaluasi lebih rapat.** Val dinilai pada epoch 4, 9, 14, ... (`--eval_every 5`). Pada dua baseline, epoch terbaik selalu epoch 9, yaitu evaluasi pertama, jadi dulu kita tidak tahu apakah epoch yang lebih awal lebih baik.
- **Efisiensi dicatat otomatis** di akhir setiap run: jumlah parameter (total dan khusus fusion), waktu inferensi per jendela, dan memori RAM puncak. Waktu latih per epoch dibaca dari log.

### 14.2 Lima varian fusion
Untuk setiap service (27 service), tiga encoder menghasilkan tiga vektor: trace (64 angka), metrics (64 angka), log (16 angka). Fusion menggabungkan ketiganya menjadi **satu vektor 64 angka per service**, yang lalu masuk ke graf. Bagian lain model tidak diubah, sehingga hanya cara penggabungan yang berbeda.

| `--fusion` | Cara kerja (sederhana) | Parameter fusion |
|---|---|---|
| `concat_glu` | Fusion asli EADRO: tempel tiga vektor, satu lapisan linear, lalu gerbang GLU | 18.560 |
| `concat_fc` | Sama seperti asli, tetapi tanpa gerbang GLU (cukup ReLU) | 9.280 |
| `sum` | Tiap sumber diproyeksikan ke 64 angka, lalu dijumlahkan. Tidak ada interaksi antar sumber | 9.408 |
| `attn` | Tiap sumber diproyeksikan, lalu model memberi bobot per sumber untuk tiap service (softmax). Bobot bisa dilihat untuk analisis | 9.473 |
| `lmf` | Low-rank multimodal fusion: perkalian antar sumber, jadi interaksi antar sumber dimodelkan langsung | 37.696 |

Angka parameter bisa diperiksa: `concat_glu` = 144 × 128 + 128 = 18.560, `concat_fc` = 144 × 64 + 64 = 9.280.

### 14.3 Uji jalan di data asli (2 epoch, `leave_event_out`, seed 42)
Keempat varian baru berjalan tanpa error dan tanpa NaN; loss turun di semuanya. Hasil 2 epoch **tidak boleh ditafsirkan** sebagai perbandingan (model baru mulai belajar, satu seed). Satu epoch ≈ 58–70 detik, memori puncak ≈ 2,8 GB, waktu inferensi ≈ 0,26–0,29 ms per jendela.

### 14.4 Rencana eksperimen
- Skema utama `leave_event_out` (Val-nya mewakili Test), 5 fusion × 3 seed (42, 7, 123), 15 epoch. Taksiran: ± 20 menit per run, ± 5 jam total di CPU.
- Metrik utama: `HR@1(std)`, `HR@3(std)`, `NDCG(std)` untuk lokalisasi, dan `F1(std)` untuk deteksi, dilaporkan sebagai rata-rata ± simpangan baku antar seed. Selisih antar fusion yang lebih kecil dari simpangan baku antar seed tidak boleh dikatakan sebagai perbedaan.
- Efisiensi: jumlah parameter, waktu latih per epoch, waktu inferensi, memori.
- `within_event` bisa ditambahkan belakangan sebagai pembanding; Val-nya tidak mewakili Test, sehingga kurang cocok sebagai skema utama.

### 14.5 Keterbatasan yang harus ditulis di laporan
1. Dari diagnosis 13.6, model baseline tampaknya banyak bersandar pada metrics, sedangkan log tidak berperan. Perbedaan antar fusion bisa lebih mencerminkan cara memproses metrics daripada kualitas penggabungan beberapa sumber.
2. Dugaan bahwa deteksi memakai ciri tingkat-run (normalisasi z-score per run) belum terbukti. Percobaan kontrol dengan normalisasi lain adalah pekerjaan lanjutan.
3. Hanya 3 seed dan satu dataset (Train Ticket); Social Network di luar cakupan.
4. Alarm palsu ± 55% pada jendela normal masih ada, sehingga F1 deteksi mencerminkan keterbatasan ini.

### 14.6 Cara menjalankan
```bash
# satu run
pipeline/run_train.sh leave_event_out 42 15 --fusion attn
# seluruh grid (berurutan, aman dihentikan lalu diulang; run yang selesai dilewati)
nohup pipeline/run_grid.sh leave_event_out 15 "42 7 123" "concat_glu concat_fc sum attn lmf" > grid_leo.out 2>&1 &
# tabel dan gambar (termasuk perbandingan fusion)
work/envs/train312/bin/python pipeline/baca_hasil.py
```
