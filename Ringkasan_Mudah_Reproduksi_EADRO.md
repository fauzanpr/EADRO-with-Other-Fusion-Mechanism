# Ringkasan mudah: apa yang sudah kita kerjakan di proyek EADRO

Dokumen ini ditulis dengan bahasa sederhana. Kalau ada istilah teknis, saya jelaskan dulu pakai perumpamaan.

---

## 1. Proyek ini sebenarnya tentang apa?

**Masalahnya.** Bayangkan sebuah aplikasi tiket kereta (namanya *Train Ticket*) yang terdiri dari 27 "bagian kecil" yang saling memanggil. Bagian kecil itu disebut *service*. Suatu hari aplikasinya jadi lambat atau error. Pertanyaannya: **bagian mana yang sakit?** Mencarinya manual itu lama dan melelahkan.

**Idenya.** EADRO (paper tahun 2023) adalah program AI yang melakukan dua hal sekaligus:

1. **Mendeteksi**: sekarang sistem sedang sakit atau sehat?
2. **Menunjuk**: kalau sakit, service mana biangnya?

**Bahan yang dipakai AI.** Seperti dokter yang melihat beberapa hasil pemeriksaan sekaligus, EADRO membaca tiga jenis data:

| Jenis data | Perumpamaan | Isinya |
|---|---|---|
| **Metrics** | Suhu badan dan tensi | CPU, memori, lalu lintas jaringan tiap service, setiap detik |
| **Traces** | Rekam jejak perjalanan | Berapa lama sebuah service menjawab panggilan dari service lain |
| **Logs** | Catatan harian pasien | Teks yang ditulis tiap service saat bekerja |

**Tugas kita (tugas kuliah).** Ada dua langkah:

1. **Mereplikasi** EADRO pada dataset Train Ticket, artinya membuktikan bahwa kita bisa menjalankannya dan mendapat hasil yang mirip paper.
2. **Mengubah cara menggabungkan tiga jenis data itu** (disebut *fusion*), lalu membandingkan mana yang paling bagus dan paling hemat. Di paper, cara penggabungan ini tidak pernah dibandingkan dengan cara lain. Di situlah kontribusi baru kita.

---

## 2. Kenapa tidak tinggal jalankan saja?

Ada dua penghalang:

**a. Data kita masih "bahan mentah".**
Dataset yang kita punya itu seperti hasil panen: sayur, daging, bumbu, belum dimasak. Kode EADRO itu seperti kompor yang hanya mau menerima bahan yang **sudah dipotong dan ditata dalam wadah tertentu**. Penulis EADRO tidak memberikan "alat pemotongnya". Jadi kita harus membuatnya sendiri.

**b. Kode EADRO-nya punya bug.**
Kodenya tidak bisa jalan apa adanya. Ada variabel yang tidak didefinisikan, nama yang salah ketik, dan sebagainya. Kodenya terakhir diperbarui tahun 2023 dan tidak ada yang merawat.

---

## 3. Apa yang sudah kita kerjakan, urut dari awal

### Langkah A. Memahami data (EDA)
Kita membuka dan memeriksa dataset: ada berapa run, apa isinya, apakah ada data yang bolong.

Temuan penting:

- Ada **9 run berisi gangguan** dan **3 run tanpa gangguan** (kondisi normal). Totalnya **12 run**.
- Ada **27 service**, tiap run punya 27 file metrics.
- Trace hanya ada untuk **9 dari 27 service**, dan log hanya untuk sekitar **13 service**. Jadi data trace dan log itu jarang.
- Data trace aslinya mengandung duplikat sekitar 4 kali dan jamnya bergeser 8 jam dari jam metrics. Kalau tidak dikoreksi, datanya tidak nyambung.

### Langkah B. Membaca dan memperbaiki kode EADRO
Kita menelusuri kodenya, menemukan **7 bug**, lalu memperbaikinya. Contohnya: ada bagian yang membuat semua fitur log bernilai sama, sehingga model tidak bisa belajar apa pun dari log. Setelah diperbaiki, kita buat **uji asap** (*smoke test*): menjalankan model dengan data buatan untuk memastikan tidak crash.

### Langkah C. Membangun "alat pemotong" untuk data mentah
Kita membuat script (di folder `pipeline/`) yang mengubah data mentah menjadi 4 jenis file yang diminta kode EADRO:

1. **Records**: kapan gangguan terjadi, di service mana, jenis apa (kunci jawaban).
2. **Metrics**: tabel angka per detik per service.
3. **Traces**: latensi per detik per pasangan service.
4. **Logs**: log yang sudah dijadikan "template", misalnya `Login user 123` dan `Login user 456` dianggap satu kejadian yang sama.

Penjelasan format yang lebih rinci ada di `work/preprocess/parsed_data/A1/Format_Data_Ekspektasi_EADRO.md`.

### Langkah D. Memotong data jadi "potongan kecil" dan membaginya
Data dipotong jadi **jendela 10 detik** yang bergeser 1 detik. Hasilnya ada sekitar **82.000 jendela**. Tiap jendela diberi label: normal, atau gangguan di service nomor sekian.

Lalu data dibagi menjadi tiga bagian, seperti ujian sekolah:

- **Train**: bahan belajar.
- **Val**: latihan soal untuk memilih versi model terbaik.
- **Test**: ujian akhir, tidak boleh diintip saat belajar.

Kita membuat **dua cara membagi**:

- `within_event`: tiap gangguan dipotong di waktu, sebagian untuk belajar dan sebagian untuk ujian.
- `leave_event_out`: ada gangguan yang **sama sekali tidak pernah dilihat** model saat belajar, jadi ujiannya lebih adil dan lebih sulit.

Kenapa dibagi dengan hati-hati? Karena jendela yang bergeser 1 detik hampir kembar. Kalau dibagi acak, jendela "kembar" bisa masuk ke train dan test sekaligus. Itu seperti memberi soal ujian yang persis sama dengan soal latihan, jadi hasilnya terlihat bagus padahal menipu. Kode asli EADRO melakukan kesalahan ini. Kita memperbaikinya.

### Langkah E. Memperbaiki cara memilih model dan cara menghitung nilai
- Kode asli memilih versi model terbaik **berdasarkan nilai test**. Itu curang, seperti memilih jawaban sambil melihat kunci. Kita ubah supaya memilih berdasarkan **Val**.
- Cara kode asli menghitung beberapa nilai ikut menghitung "normal ditebak normal" sebagai benar, sehingga angkanya tercampur. Kita **tetap mencetak angka asli** dan menambahkan versi bertanda **(std)** yang hanya menilai jendela bergangguan. Jadi kita bisa membandingkan dengan paper maupun dengan versi yang lebih jernih.

### Langkah F. Melatih model baseline
Baseline artinya model EADRO versi asli (belum kita utak-atik fusion-nya). Kamu menjalankannya sendiri di laptop, dan hasilnya sama persis dengan yang saya jalankan, jadi hasilnya bisa diulang.

### Langkah G. Menyelidiki kenapa hasilnya belum sebagus paper
Lihat bagian 4 di bawah.

### Langkah H. Menyiapkan 5 cara fusion
Kode sudah punya 5 pilihan cara menggabungkan tiga jenis data, tinggal dipilih lewat satu argumen `--fusion`:

| Nama | Cara kerja singkat |
|---|---|
| `concat_glu` | Cara asli paper: tempel ketiganya, lalu saring |
| `concat_fc` | Tempel, lalu proses lebih sederhana |
| `sum` | Jumlahkan saja |
| `attn` | Biarkan model menentukan bagian mana yang lebih penting |
| `lmf` | Cara gabung berbasis perkalian |

Script untuk menjalankan semuanya sekaligus (`pipeline/run_grid.sh`) sudah siap, dan modelnya sudah diuji jalan.

### Langkah I. Laporan
Slide Progress 3 sudah diisi bagian EDA dan Baseline. Penjelasan untuk belajar ada di `Report/Penjelasan_EDA_dan_Baseline.md`.

---

## 4. Hasilnya sejauh ini, dengan jujur

| | Paper (Train Ticket) | Kita (baseline) |
|---|---|---|
| F1 (kualitas deteksi) | sekitar 0,989 | sekitar 0,78 (`leave_event_out`) |
| HR@1 (tebakan pertama benar) | sekitar 0,990 | sekitar 0,54 (`leave_event_out`) dan sekitar 0,81 (`within_event`) |

Angkanya belum sebagus paper. Ini temuan dari penyelidikan:

1. **Model terlalu sering salah alarm.** Pada data normal, ia sering mengira ada gangguan. Penyebabnya masih dugaan dan belum terbukti.
2. **Model hampir hanya mengandalkan metrics.** Saat log dimatikan (diisi nol), hasilnya tidak berubah. Saat metrics dimatikan, alarm hilang semua. Ini artinya "penggabungan tiga jenis data" di pipeline kita sekarang praktis hanya memakai satu jenis. Itu masalah untuk perbandingan fusion, karena sulit melihat perbedaan antar cara fusion kalau yang dipakai cuma satu sumber.
3. **Data kita lebih sedikit dan lebih berantakan** daripada milik paper: hanya 9 run berisi gangguan (paper menulis jumlah yang lebih besar), dan trace serta log sangat jarang.

Jadi **angka paper tidak boleh dianggap target pasti**. Yang penting adalah proses kita jujur dan semua penyimpangan dari paper dicatat.

---

## 5. Apa yang belum dikerjakan

1. **Menjalankan perbandingan 5 cara fusion** (rencananya 5 fusion × 3 seed, sekitar 5 jam komputasi CPU). Script dan kodenya siap, tetapi belum dijalankan.
2. **Memutuskan apa yang dilakukan dengan masalah alarm palsu.** Pilihannya: (1) perbaiki cara normalisasi data lalu latih ulang, (2) latih dengan sebagian kanal dimatikan untuk melihat perannya, atau (3) catat sebagai keterbatasan di laporan lalu lanjut. Rekomendasi saya adalah pilihan (1).
3. **Menyamakan slide dengan kode.** Slide 11 menulis 4 kandidat fusion termasuk Cross-Attention, sedangkan kode punya 5 kandidat dan Cross-Attention belum ada.

---

## 6. Peta file, supaya tidak tersesat

| Lokasi | Isinya |
|---|---|
| `TT Dataset/` | Data mentah asli |
| `Eadro/codes/` | Kode EADRO yang sudah kita perbaiki |
| `pipeline/` | Script buatan kita: pengolah data, pembagi data, pelatih, pembaca hasil |
| `work/preprocess/parsed_data/A1/` | Data setelah diolah (format yang diminta EADRO) |
| `work/chunks/A1/` | Data siap latih (sudah dipotong jendela dan dibagi train/val/test) |
| `work/result/` | Hasil pelatihan dan grafik |
| `Penjelasan_Pekerjaan_EADRO.md` | Penjelasan teknis lengkap (lebih rinci dari dokumen ini) |
| `Report/` | Slide dan panduan belajar laporan |
| `EDA*.ipynb`, `Hasil_Training.ipynb` | Notebook untuk melihat data dan hasil |

---

## 7. Kalau hanya mau ingat satu paragraf

EADRO adalah AI yang mencari service yang sakit dari tiga sumber data. Dataset kita masih mentah dan kode asli punya bug, jadi kita membuat sendiri pengolah datanya, memperbaiki 7 bug, membagi data dengan adil, dan sudah melatih baseline-nya. Hasilnya belum sebagus paper, dan penyebab utamanya adalah alarm palsu serta model yang hampir hanya memakai metrics. Langkah berikutnya: memutuskan cara menangani hal itu, lalu menjalankan perbandingan 5 cara fusion, yang merupakan inti kontribusi tugas ini.
