# Panduan Belajar: EDA dan Baseline Reproduction EADRO

Dokumen ini menemani slide 16–29 di `Progress 3.pptx`. Tujuannya: setelah membaca ini, Anda bisa menjelaskan tiap slide dengan kata-kata sendiri dan menjawab pertanyaan dosen.

Cara membaca: urut dari atas. Bagian 1–2 adalah bekal dasar. Bagian 3 menjelaskan slide EDA, Bagian 4 slide Baseline. Bagian 5–7 berisi cara membaca metrik, hal yang harus jujur disampaikan, dan latihan tanya-jawab.

---

## 1. Gambaran besar dalam 5 kalimat

1. Proyek Anda membandingkan **cara menggabungkan beberapa jenis data (fusion)** di model EADRO untuk mencari service penyebab gangguan.
2. Sebelum membandingkan, kita perlu **baseline**: EADRO asli yang berjalan benar di data kita. Tanpa baseline yang layak, perbandingan fusion tidak bermakna.
3. **EDA** (Exploratory Data Analysis) adalah tahap mengenali data: apa isinya, apa yang kurang, apa yang aneh.
4. Dari EDA kita tahu data Train Ticket (TT) kita lebih kecil dari paper dan banyak yang perlu dibersihkan.
5. Baseline yang sudah kita latih **belum mendekati angka paper**. Kita sudah tahu sebagian penyebabnya, dan itu hal yang wajar dilaporkan dalam laporan kemajuan.

---

## 2. Istilah dasar (baca dulu, jangan dihafal)

| Istilah | Arti sederhana | Contoh di data Anda |
|---|---|---|
| **Microservice / service** | Aplikasi besar yang dipecah jadi program-program kecil yang saling memanggil. | `ts-food-service`, `ts-order-service`. Ada 27. |
| **Node** | Sebutan model untuk satu service. | 27 node. |
| **Fault injection** | Sengaja merusak satu service untuk uji coba, lalu merekam dampaknya. | CPU dibebani, jaringan dilambatkan. |
| **Culprit / biang** | Service yang sengaja dirusak. Model harus menebak ini. | `ts-food-service` pada fault pertama run 0. |
| **Metrics** | Angka yang diukur tiap detik. | CPU, memori, lalu lintas jaringan (7 angka per service). |
| **Logs** | Catatan teks yang ditulis program. | `Route id: <UUID>`. |
| **Traces** | Rekaman satu permintaan yang mengalir antar-service, termasuk lama tiap langkah. | Latensi (ms) dari service A ke B. |
| **Modalitas** | Satu jenis data. Metrics, logs, traces adalah 3 modalitas. | "Multimodal" = memakai beberapa sekaligus. |
| **Window / jendela** | Potongan waktu pendek yang jadi satu contoh bagi model. | 10 detik, digeser 1 detik tiap kali. |
| **Label** | Jawaban benar yang dipakai untuk melatih dan menilai model. | "Jendela ini bergangguan" atau "normal". |
| **Train / Val / Test** | Tiga bagian data. Train untuk belajar, Val untuk memilih pengaturan, Test untuk nilai akhir. | 40.510 / 7.490 / 32.190 jendela (`within_event`). |
| **Epoch** | Satu putaran model membaca seluruh data latih. | Kita memilih epoch 9. |
| **Seed** | Angka awal untuk keacakan. Seed beda bisa memberi hasil beda sedikit. | Baru seed 42. |
| **Fusion** | Cara menggabungkan fitur dari tiga modalitas menjadi satu representasi. | EADRO asli: gabung, lalu FC, lalu GLU. |
| **Alarm palsu** | Model bilang "bergangguan" padahal sebenarnya normal. | 57,9% jendela normal di Test. |

Dua istilah metrik (penjelasan lengkap di Bagian 5):

- **Precision (presisi):** dari semua yang dibunyikan alarm, berapa yang benar-benar gangguan?
- **Recall:** dari semua gangguan yang ada, berapa yang berhasil terdeteksi?

---

## 3. Bagian EDA (slide 17–21)

### Slide 17: Dataset Train Ticket (TT)

**Isi slide:** 12 run, 27 service, 81 kejadian fault, 82.350 jendela, dan gambar isi satu run.

**Penjelasan:**

- **Train Ticket** adalah aplikasi pemesanan tiket kereta yang sengaja dibuat sebagai bahan penelitian. Terdiri dari 27 service yang kita pantau.
- Satu **run** = satu sesi pengamatan. Ada **9 run berisi fault** dan **3 run normal** (tidak ada yang dirusak, dipakai sebagai contoh kondisi sehat).
- Di setiap run berfault, 3 service dirusak, masing-masing dengan 3 jenis fault, jadi 9 fault per run. Tiap fault berlangsung ±10 menit (600 detik), dengan jeda ±114 detik di antaranya.
  - `cpu_load`: CPU service dibebani.
  - `network_delay`: jaringan service diperlambat.
  - `network_loss`: sebagian paket jaringan dibuang.
- 9 run × 9 fault = **81 kejadian fault** (27 service × 3 jenis). Paper melaporkan **162**, jadi data kita separuh. Akibatnya angka kita tidak bisa dibandingkan satu lawan satu dengan paper.
- **82.350 jendela**: seluruh rekaman dipotong menjadi jendela 10 detik, digeser 1 detik tiap kali. 59,9% di antaranya jendela bergangguan.

**Poin yang sering terlewat:** 82.350 itu bukan 82.350 kejadian berbeda. Jendela bertetangga hampir sama persis (hanya geser 1 detik). Kejadian yang benar-benar berbeda hanya **81**. Ini penting untuk cara membagi data (lihat slide 24).

### Slide 18: Tiga modalitas, cakupan tidak merata

**Isi slide:** grafik jumlah service yang punya data per modalitas (Metrics 27, Logs ±14, Traces 9) dan tiga kartu penjelasan.

**Penjelasan per modalitas:**

- **Metrics: lengkap.** 27 service × 7 angka (3 tentang CPU, 2 tentang memori, 2 tentang jaringan) setiap detik. Data bersih, tanpa celah atau nilai kosong.
- **Logs: banyak tapi monoton.** 124.571 baris log. Setelah dikelompokkan menjadi pola (disebut *template*) oleh alat bernama Drain3, hanya ada 59 pola. Sebanyak 40,2% baris adalah satu pola yang sama, `Span reported: ...`. Per run, hanya 13–15 dari 27 service yang menulis log.
- **Traces: jarang.** Hanya 9 dari 27 service yang pernah menjadi tujuan panggilan terlacak. Bahkan pada 9 service itu, hanya ±15% jendela 10 detik berisi minimal satu rekaman.

**Kenapa penting:** EADRO diharapkan menggabungkan tiga sumber data. Kalau dua di antaranya tipis, model cenderung bersandar pada yang paling lengkap (metrics). Ini muncul lagi di slide diagnosis (slide 27).

### Slide 19: Dari data mentah ke input model

**Isi slide:** tabel tiga baris (Metrics, Traces, Logs) yang menunjukkan data mentah, cara pengolahan, dan bentuk akhir yang masuk model.

**Penjelasan:** model tidak bisa membaca file CSV atau teks mentah. Semuanya harus diubah menjadi **tensor** (susunan angka dengan bentuk tetap):

| Modalitas | Bentuk | Artinya |
|---|---|---|
| Metrics | 27 × 10 × 7 | 27 service, 10 detik, 7 angka per detik |
| Traces | 27 × 10 | latensi per detik untuk tiap service |
| Logs | 27 × 60 | untuk tiap service, seberapa aktif tiap pola log (60 = 59 pola + 1 pola "belum pernah terlihat") |

Beberapa istilah di slide itu:

- **Z-score per run:** setiap angka dikurangi rata-rata lalu dibagi simpangan baku, dihitung per run. Tujuannya membuat angka dari kanal berbeda (CPU, memori, jaringan) berskala sebanding.
- **Hawkes:** model statistik yang menghitung seberapa "ramai" sebuah pola log dalam jendela. Hasilnya angka per pola.
- **Label:** jendela dianggap bergangguan bila ada fault di dalamnya (batas: minimal 1 detik).

**Temuan penting:** jam di `spans` dan `logs` ternyata **selisih 8 jam** dari jam label dan metrics (kemungkinan perbedaan zona waktu). Setelah digeser 8 jam, data cocok. Tanpa penggeseran, hampir tidak ada log atau span yang jatuh di dalam jendela.

### Slide 20: Fault meninggalkan jejak di modalitas berbeda

**Isi slide:** matriks 3 jenis fault × 2 jenis data (metrics service biang, latensi trace service biang).

**Hasil pengukuran kita sendiri:**

| Jenis fault | Metrics service biang | Latensi trace service biang |
|---|---|---|
| `cpu_load` | Terlihat jelas (lonjakan ±30× ukuran variasi normal, pulih cepat) | Tidak naik (×0,75 dari normal) |
| `network_delay` | Hampir tidak bereaksi | Naik ±3.000× (median) |
| `network_loss` | Hampir tidak bereaksi | Naik ±900× (median) |

**Cara membaca:** fault CPU "berteriak" di metrics, fault jaringan "berteriak" di trace. Tidak ada satu jenis data yang menangkap semuanya. Inilah **alasan ilmiah kenapa EADRO memakai beberapa modalitas sekaligus**, dan alasan fusion layak diteliti.

**Catatan jujur:** pada 54 dari 81 fault, service biangnya **tidak punya data trace sama sekali** (hanya 27 fault yang biangnya termasuk 9 service ber-trace). Jadi untuk sebagian besar fault, trace tidak bisa membantu.

Angka latensi dihitung dengan membandingkan median latensi saat fault dan median di jeda normal pada run yang sama, untuk service biang yang punya trace. Rentang antar kejadian lebar (`network_delay`: ×1.500–4.300; `network_loss`: ×270–6.100), jadi pakai kata "±" dan "median".

### Slide 21: Temuan penting dari EDA

Enam temuan. Dua yang paling sering ditanyakan:

1. **Jam bergeser 8 jam.** Ini bukan bug model, tapi sifat data. Kalau tidak dikoreksi, log dan trace tidak sejajar dengan label sehingga model belajar dari data yang salah waktu.
2. **Hanya 81 kejadian independen.** Bila kita membagi 82.350 jendela secara acak ke train dan test, jendela yang hampir kembar bisa masuk ke dua sisi sekaligus. Model seolah "menghafal" soal ujian. Itu disebut **kebocoran data (data leakage)** dan membuat hasil tampak lebih bagus dari kenyataan.

Empat temuan lain: span duplikat ±4×, trace dan log tipis, data separuh dari paper, dan pipeline pemrosesan tidak disediakan penulis paper.

---

## 4. Bagian Baseline Reproduction (slide 23–29)

### Slide 23: Kode EADRO tidak bisa jalan apa adanya

Kode dari GitHub penulis berhenti dengan error bila dijalankan. Kami memperbaiki **7 bug utama**:

1. Argumen `edges` tidak diteruskan ke `chunkDataset`.
2. `trace_dropout` dan `metric_dropout` dipakai tapi tidak pernah didefinisikan.
3. Nama atribut model tidak konsisten (misalnya `localizer` vs `locator`).
4. `np` (numpy) dipakai tanpa di-import, sehingga berhenti saat epoch 9, tepat ketika evaluasi pertama.
5. Kanal trace tidak cocok (data 2 kanal, model 1 kanal). Karena paper menyebut deret latensi *univariate*, yang diubah adalah pembuatan datanya, bukan modelnya.
6. `align.py`: variabel `chunks` belum ada ketika file cache sudah tersedia.
7. Perhitungan Hawkes memakai waktu absolut (detik sejak 1970), bukan panjang jendela. Akibatnya semua fitur log bernilai sama (konstan), jadi modalitas log tidak membawa informasi apa pun.

Selain itu, **kode untuk mengubah data mentah menjadi input model tidak ada** (baik di GitHub maupun Zenodo). Kami membangunnya sendiri. Ada juga salinan (*fork*) kode dari pihak lain, tapi tidak kami pakai karena di salinan itu 0 dari 83.567 baris log jatuh di jendela, jadi modalitas log kosong.

**Mengapa smoke test:** sebelum memakai data asli, kami menjalankan model pada data buatan. Tujuannya memastikan kodenya berjalan dan hasilnya sama setiap kali dijalankan (deterministik).

### Slide 24: Penyesuaian terhadap protokol asli

Ini hal-hal yang **sengaja berbeda** dari kode asli, beserta alasannya.

| Aspek | Kode asli | Kita | Alasan |
|---|---|---|---|
| Data | 162 injeksi, TT dan SN | 81 injeksi, hanya TT | Itu data yang kita punya |
| Pembagian data | Acak per jendela | `within_event` dan `leave_event_out` | Mencegah kebocoran data |
| Pilih epoch | Pakai Test set | Pakai Val set | Test tidak boleh dipakai memilih; itu mengintip jawaban |
| Metrik | Mencampur kelas normal | Ditambah versi (std) | Lihat Bagian 5 |
| Fitur log | Bug waktu | Diperbaiki | Lihat bug #7 |
| Lingkungan | torch 1.12.1 | torch 2.2.1 CPU | Versi lama tidak bisa dipasang di Python 3.12 |

**Dua skema pembagian data:**

- **`within_event`:** setiap wilayah fault dipotong 50% awal untuk Train, 10% untuk Val, 40% akhir untuk Test (menurut urutan waktu). Jadi setiap kejadian muncul di ketiganya, tapi bagian waktunya tidak saling tumpang tindih (ada jarak pemisah per detik).
- **`leave_event_out`:** satu jenis fault pada satu service **sama sekali tidak pernah dilihat** model saat Train. Ini lebih sulit tapi lebih jujur: menguji apakah model bisa mengenali gangguan yang belum pernah dilihat.

Hyperparameter model (`lr = 1e-3`, `epoches = 50`, `patience = 5`) **tidak diubah**. Yang diubah hanya protokol evaluasi.

### Slide 25 dan 26: Hasil baseline vs paper

Hasil di Test set, seed 42, epoch terpilih 9. Metrik versi (std):

| | F1 | HR@1 | HR@3 | HR@5 |
|---|---|---|---|---|
| **Paper (TT)** | 0,989 | 0,990 | 0,992 | 0,993 |
| `within_event` | 0,765 | 0,808 | 0,875 | 0,889 |
| `leave_event_out` | 0,780 | 0,539 | 0,666 | 0,731 |

**Cara membaca:**

- **F1** menilai *deteksi*: apakah model tahu "ada gangguan atau tidak".
- **HR@k** menilai *lokalisasi*: apakah service biang yang benar ada di k tebakan teratas.
- Kita jauh di bawah paper pada keduanya. Selisih terbesar ada pada lokalisasi di `leave_event_out` (0,54 vs 0,99).
- `leave_event_out` lebih rendah dari `within_event` karena soalnya lebih sulit (jenis fault tertentu tidak pernah dilihat saat belajar).

Slide 26 menambahkan NDCG@3, NDCG@5, serta versi **(asli)**, yaitu rumus persis dari kode EADRO. Kami cetak keduanya supaya transparan.

**Peringatan:** ini baru **satu seed**. Kita belum tahu seberapa besar angka berubah bila diulang.

### Slide 27: Mengapa jauh di bawah paper?

Kami menyelidiki dengan menjalankan model pada semua jendela lalu menghitung **alarm palsu** (jendela normal yang ditandai bergangguan).

**Temuan 1: masalahnya di presisi.** Di Test: recall (std) 0,90 (bagus), presisi (std) 0,66 (paper: 0,98). Artinya hampir semua gangguan terdeteksi, tapi banyak jendela normal ikut ditandai. Persentase jendela normal yang salah ditandai: Train 19,0%, Val 11,8%, **Test 57,9%**.

**Temuan 2: jendela "celah" dianggap fault.** Jendela normal di antara dua fault (pada run berfault) ditandai gangguan ±80%, **bahkan pada data latih**. Itu bukan masalah generalisasi; model memang belum belajar membedakan "celah" dari "gangguan". Penyebabnya belum diketahui. Kemungkinannya: efek sisa gangguan yang belum pulih, atau batas waktu label tidak persis sama dengan efek sebenarnya. Untuk gangguan CPU, kami cek: efek CPU berhenti segera setelah fault, jadi kemungkinan "efek sisa" tidak terbukti pada CPU.

**Temuan 3: model bersandar pada metrics.** Kami "mematikan" (menolkan) satu modalitas pada model yang sudah dilatih:

- Log dinolkan: **tidak ada perubahan sama sekali**. Log nyaris tidak berperan.
- Kanal memory dinolkan: **semua alarm hilang**. Model sangat bergantung pada memory.
- Kanal CPU dinolkan: recall turun dari 90% ke 60%.

**Catatan kehati-hatian:** menolkan input bukan kondisi data nyata. Hasil ini adalah **petunjuk arah, bukan bukti pasti**. Hipotesis kami: deteksi banyak bersandar pada ciri tingkat-run (skala data per run), bukan pada efek gangguan di service biang. Itu **belum terbukti**.

**Mengapa ini penting untuk proyek fusion:** bila model hampir hanya memakai metrics, maka mengganti cara fusion mungkin hanya mengubah cara memproses metrics, bukan cara menggabungkan beberapa sumber. Ini harus dicatat sebagai keterbatasan.

### Slide 28: Baseline Acceptance Check

Mencocokkan kondisi saat ini dengan 5 kriteria di slide 10:

| Kriteria | Status | Ringkasan |
|---|---|---|
| Pipeline Correctness | Terpenuhi | Smoke test, verifikasi dengan fungsi asli |
| Architectural Fidelity | Terpenuhi | Komponen inti dan hyperparameter dipertahankan |
| Experimental Consistency | Sebagian | Split bersih, tapi Val di `within_event` kurang mewakili Test |
| Performance Sanity | Belum | Jauh di bawah paper, sedang didiagnosis |
| Training Stability | Belum | Baru 1 seed |

Alasan Val di `within_event` kurang mewakili: seluruh jendela normal di Val berasal dari run tanpa fault. Tidak ada satu pun jendela "celah" (masalah terbesar) di Val. Karena itu Val tampak bagus (presisi 0,94) padahal Test buruk (presisi 0,66). Skema `leave_event_out` memperbaiki hal ini.

### Slide 29: Langkah selanjutnya

1. **Perbaiki alarm palsu**: normalisasi yang tidak bergantung pada run (statistik dihitung dari data normal saja), latih ulang 15–20 epoch.
2. **Ukur stabilitas**: 3 seed (42, 7, 123), laporkan rata-rata ± simpangan baku.
3. **Jalankan perbandingan fusion**: kode 5 varian sudah siap (`concat_glu`, `concat_fc`, `sum`, `attn`, `lmf`). Rencana 5 varian × 3 seed, ±20 menit per run, total ±5 jam di CPU.

---

## 5. Cara membaca F1 dan HR@1 dengan contoh

### F1, presisi, recall

Bayangkan di Test ada **100 jendela bergangguan**. Model membunyikan alarm pada **150 jendela**, dan **90** di antaranya memang bergangguan.

- Recall = 90 / 100 = **0,90** (dari 100 gangguan, 90 tertangkap)
- Presisi = 90 / 150 = **0,60** (dari 150 alarm, hanya 90 yang benar; 60 alarm palsu)
- F1 = 2 × presisi × recall / (presisi + recall) = 2 × 0,60 × 0,90 / 1,50 = **0,72**

F1 adalah rata-rata "harmonis" keduanya: ia rendah bila salah satunya rendah. Pada hasil kita: recall (std) 0,90 dan presisi (std) 0,66 memberi F1 ≈ 0,76, sesuai tabel. Terlihat bahwa **presisi** yang menarik F1 turun.

### HR@k (Hit Rate)

Untuk tiap jendela bergangguan, model memberi urutan service dari yang paling dicurigai.

- **HR@1:** persentase jendela di mana service biang berada di **urutan pertama**.
- **HR@3:** biang ada di **3 teratas**. **HR@5:** di 5 teratas.

Contoh: biangnya `ts-food-service`. Bila model mengurutkan `[ts-order, ts-food, ts-user, ...]`, maka HR@1 = tidak kena, HR@3 = kena. Acak murni pada 27 service memberi HR@1 ≈ 1/27 = 0,037, jadi hasil 0,81 jelas jauh di atas tebakan acak.

### NDCG@k

Mirip HR@k, tapi memberi skor lebih besar bila biang ada **lebih atas** dalam daftar. Pada k=1, NDCG@1 sama dengan HR@1 (itu sebabnya paper tidak menampilkan NDCG@1).

### Kenapa ada versi (std) dan versi (asli)?

Saat membaca kode asli, kami menemukan kode itu menghitung jendela **normal yang tertebak normal** sebagai "benar" (TP), padahal definisi F1 yang umum hanya menghitung kelas gangguan. Akibatnya:

- F1, recall, presisi bercampur dua kelas.
- Penyebut HR@k ikut membesar (menghitung jendela normal yang benar), sehingga HR@k hanya bisa mencapai ±0,74 pada Test `within_event` meski modelnya sempurna dalam menebak biang.

Karena itu kami **tetap mencetak angka asli** (agar bisa dicek) dan **menambah versi (std)** yang hanya menghitung jendela bergangguan. Untuk membandingkan dengan paper, versi (std) lebih sesuai dengan definisi di paper. Kami memverifikasi versi (std) terhadap hitungan independen dengan selisih di bawah 1e-9.

---

## 6. Hal yang harus disampaikan dengan jujur

1. **Hasil belum mendekati paper.** F1 ≈ 0,77 vs 0,989. HR@1 0,81 dan 0,54 vs 0,990.
2. **Data kita separuh dari paper** (81 vs 162 injeksi) dan hanya TT. Angka tidak bisa dibandingkan satu lawan satu.
3. **Kode asli tidak jalan.** Kami memperbaiki 7 bug dan membangun pipeline sendiri. Ini deviasi yang terdokumentasi, bukan "reproduksi persis".
4. **Pembagian data dan pemilihan epoch berbeda dari kode asli** (demi menghindari kebocoran data).
5. **Baru satu seed.** Belum ada ukuran variasi.
6. **Model diduga bersandar pada metrics; log nyaris tidak berperan.** Ini hipotesis, belum terbukti. Dampaknya pada perbandingan fusion harus dicatat.
7. **Val di `within_event` kurang mewakili Test.** Itu cacat rancangan skema yang kami buat, dan kami sudah memperbaikinya lewat `leave_event_out`.
8. **Fitur log dari Hawkes** nyaris hanya menandai "ada log atau tidak" (nilai jenuh ±0,1), setia pada kode asli tapi lemah sebagai sinyal.

---

## 7. Latihan tanya-jawab (kemungkinan pertanyaan dosen)

**T: Kenapa hasil Anda jauh di bawah paper?**
J: Ada beberapa sebab yang sudah kami identifikasi: data separuh dari paper, kode asli tidak bisa jalan (diperbaiki dan beberapa pengaturan berbeda), dan pembagian data kami lebih ketat (tanpa kebocoran). Yang paling kuat: presisi deteksi rendah karena banyak alarm palsu pada jendela normal (57,9% di Test), terutama jendela di antara dua fault. Penyebab pastinya masih kami selidiki.

**T: Apa bedanya `within_event` dan `leave_event_out`?**
J: `within_event` memotong tiap wilayah fault menurut waktu, jadi model pernah melihat jenis gangguan yang sama di Train. `leave_event_out` menahan satu jenis fault pada satu service sepenuhnya untuk Test, jadi lebih sulit dan lebih jujur.

**T: Kenapa tidak memakai pembagian acak seperti kode asli?**
J: Jendela digeser 1 detik sehingga tetangganya hampir kembar. Pembagian acak menaruh kembarannya di Train dan Test sekaligus, membuat hasil tampak terlalu bagus. Kejadian yang benar-benar independen hanya 81.

**T: Kenapa F1 versi asli dan (std) berbeda?**
J: Kode asli menghitung jendela normal yang tertebak benar sebagai "benar" juga. Versi (std) hanya menghitung kelas gangguan sesuai definisi F1 dan HR@k di paper. Kami tampilkan keduanya.

**T: Apakah baseline sudah layak untuk dibandingkan dengan fusion lain?**
J: Belum sepenuhnya. Pipeline dan arsitektur sudah sesuai, tapi performa belum masuk akal dan stabilitas belum diuji. Perbandingan fusion kami jalankan setelah dua hal itu terpenuhi, dan selisih antar varian yang lebih kecil dari simpangan baku antar seed tidak kami anggap perbedaan.

**T: Apa kontribusi proyek ini?**
J: Paper EADRO tidak pernah membandingkan mekanisme fusion (hanya satu cara: gabung, FC, GLU). Kami membandingkan beberapa varian di bawah protokol yang sama, dari sisi efektivitas (F1, HR@k, NDCG@k) dan efisiensi (jumlah parameter, waktu, memori).

---

## 8. Dari mana angka-angka ini berasal

Agar bisa diperiksa ulang (semua di `/home/ojan/AI Labs/EADRO - APDM/`):

| Informasi | Sumber |
|---|---|
| Hasil F1, HR@k, NDCG@k | `work/result/ringkasan_hasil.csv`, `work/result/experiments.txt` |
| Alarm palsu per split | `work/result/9df622b8/diagnosis_alarm.csv` |
| Percobaan mematikan input | `work/result/9df622b8/diagnosis_ablasi.csv` |
| Jumlah jendela per split | `work/chunks/A1/<skema>/split_summary.json` |
| Statistik log | `work/preprocess/parsed_data/A1/logs_summary.json` |
| Daftar run dan fault | `work/preprocess/parsed_data/A1/manifest.json`, `records*.json` |
| Angka paper (TT) | Tabel II, III, IV pada PDF paper di folder proyek |
| Penjelasan teknis lengkap | `Penjelasan_Pekerjaan_EADRO.md` (Bagian 13 dan 14) |
| Kode yang dimodifikasi | `Eadro/codes/` (perubahan terlihat lewat `git diff`) |

Run yang dipakai: `9df622b8` (`within_event`) dan `d574273b` (`leave_event_out`), keduanya seed 42.

---

## 9. Catatan untuk Anda sebagai penyusun laporan

- **Slide 11 menyebut 4 kandidat fusion (F1–F4)**, sedangkan kode sudah memiliki **5 varian**: `concat_glu` (asli), `concat_fc`, `sum`, `attn` (bobot per modalitas lewat softmax), dan `lmf` (low-rank multimodal fusion). Varian "Cross-Attention" ala FAMOS yang tercantum di slide 11 **belum ada di kode**, dan `sum` serta `lmf` belum tercantum di slide. Anda perlu menyamakan keduanya sebelum presentasi akhir.
- Slide 9 menyebut membandingkan HR@K dan NDCG@K dengan paper; itu sudah ada di slide 26.
- Deck memakai font EB Garamond dan DM Sans (sama seperti slide Anda yang sudah ada). Bila font itu belum terpasang di komputer presentasi, PowerPoint akan menggantinya otomatis dan tampilan bisa sedikit bergeser.
- Catatan pembicara (*speaker notes*) berbahasa sederhana sudah saya tambahkan di tiap slide baru (lihat di mode Presenter).
