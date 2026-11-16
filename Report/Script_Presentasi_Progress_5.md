# Script Presentasi Progress 5

Pasangan dari `PPT Progress/Progress 5.pptx` (24 slide). Dibuat 17 November 2026.

Total waktu kalau dibawakan apa adanya: sekitar 30 menit. Kalau waktunya cuma 15 sampai 20 menit, bagian yang bisa dipersingkat ada di catatan "Kalau waktunya mepet" di akhir dokumen.

Tiap slide punya tiga bagian:

- **Yang diucapkan.** Teks untuk dibawakan. Tidak perlu dihafal kata per kata, yang penting alurnya.
- **Supaya paham.** Penjelasan di balik slide, untuk kamu sendiri. Bagian ini tidak perlu diucapkan.
- **Kalau ditanya.** Pertanyaan yang mungkin muncul dan cara menjawabnya.

---

## Bagian 0. Istilah yang sering muncul

Baca bagian ini dulu sebelum latihan. Hampir semua slide memakai istilah-istilah ini.

**Window dan T.** Data monitoring (log, metrics, trace) itu deret waktu per detik. Model tidak membaca seluruh rekaman sekaligus, tapi potongan pendek yang disebut window. T adalah panjang potongan itu dalam detik. T = 10 berarti satu window berisi 10 detik data. Window digeser 1 detik setiap kali, jadi window ke-1 berisi detik 1 sampai 10, window ke-2 berisi detik 2 sampai 11, dan seterusnya. Dua window yang bersebelahan isinya hampir sama (9 dari 10 detik).

**Tiga modalitas.** Log (catatan teks dari aplikasi), metrics (angka seperti CPU dan memori), dan trace (jejak satu permintaan yang lewat beberapa service). EADRO memakai ketiganya sekaligus, makanya disebut multimodal.

**Fault dan root cause.** Fault adalah gangguan yang sengaja disuntikkan ke sistem Train Ticket (misalnya CPU dibuat penuh di satu service). Root cause adalah service tempat gangguan itu disuntikkan. Train Ticket punya 27 service.

**Dua tugas EADRO.**
1. Deteksi: window ini normal atau ada gangguan?
2. Lokalisasi: kalau ada gangguan, service mana root cause-nya? Model mengurutkan 27 service dari yang paling dicurigai.

**Train, Val, Test.** Data dibagi tiga. Train untuk melatih model. Val (validation) untuk memilih epoch terbaik. Test untuk nilai akhir, dan seharusnya tidak pernah dilihat model selama training.

**Split.** Cara membagi data ke Train, Val, dan Test. Ada tiga cara di proyek ini:
- `within_event`: tiap kejadian fault dipotong menurut waktu. 50% awal masuk Train, 10% berikutnya Val, 40% terakhir Test. Model sudah pernah melihat awal dari kejadian yang sama, jadi ini menguji "event yang sudah dikenal".
- `leave_event_out`: sebagian jenis fault untuk tiap service disimpan khusus untuk Test dan sama sekali tidak muncul di Train. Ini menguji "fault baru". Paling sulit, paling mirip kondisi nyata.
- `random_original`: meniru kode rilis EADRO. Semua window diacak lalu dibagi 70/30.

**Data leakage.** Informasi dari Test bocor ke Train. Di `random_original`, window detik 1 sampai 10 bisa masuk Train sementara window detik 2 sampai 11 masuk Test. Isinya hampir sama, jadi model seperti sudah melihat soal ujiannya.

**Epoch.** Satu putaran penuh model belajar dari seluruh data Train. 15 epoch berarti 15 putaran.

**Seed.** Angka awal untuk proses acak (inisialisasi bobot, urutan data). Seed berbeda menghasilkan model yang sedikit berbeda. Kita pakai 3 seed (42, 7, 123) lalu melaporkan rata-rata dan sd (simpangan baku). sd besar artinya hasilnya sangat tergantung keberuntungan.

**Metrik deteksi.**
- Recall: dari semua window gangguan, berapa persen yang tertangkap.
- Precision: dari semua alarm yang dibunyikan model, berapa persen yang memang gangguan.
- F1: gabungan Precision dan Recall dalam satu angka.
- False alarm (FPR): dari semua window normal, berapa persen yang salah dianggap gangguan. Ini tidak dicatat langsung oleh kode, saya hitung dari Precision, Recall, dan jumlah window.

**Metrik lokalisasi.**
- HR@1 (hit rate at 1): seberapa sering root cause yang benar ada di urutan pertama.
- HR@3: seberapa sering root cause ada di 3 besar.
- NDCG@k: mirip HR@k, tapi memberi nilai lebih kalau root cause ada di urutan lebih atas.

**Metrik (std).** Versi metrik yang saya hitung sendiri dengan rumus standar: hanya window gangguan yang dihitung. Dipakai karena rumus HR@k di kode rilis EADRO bermasalah (slide 8).

**Fusion.** Cara menggabungkan informasi dari tiga modalitas menjadi satu representasi sebelum diproses lebih lanjut. Topik utama proyek ini adalah membandingkan beberapa cara fusion.

---

## Slide 1. Progress 5

*Durasi: 15 detik*

**Yang diucapkan:**

"Selamat pagi, Bapak/Ibu. Saya akan menyampaikan Progress 5 dari proyek replikasi EADRO dan perbandingan mekanisme fusion pada dataset Train Ticket."

---

## Slide 2. Review Progress 4

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Sebelum masuk ke progress minggu ini, saya ulang singkat posisi kita di Progress 4.

Pertama, baseline EADRO dengan 3 seed. F1-nya 0,77 di within_event dan 0,81 di leave_event_out. HR@1-nya 0,82 dan 0,65. Paper melaporkan sekitar 0,99, jadi selisihnya jauh.

Kedua, variasi antar seed besar. Di leave_event_out, HR@1 bisa 0,57 atau 0,76 hanya karena seed-nya berbeda.

Ketiga, false alarm tinggi. Recall sudah 0,92 sampai 0,94, tapi sekitar 60% window normal ikut dianggap gangguan.

Keempat, T = 5 dan T = 10 belum bisa dibedakan performanya, walaupun T = 5 lebih cepat dan lebih hemat memori.

Kelima, trace di data ini datang per menit. Hanya 18% window T = 10 yang berisi trace.

Dan terakhir, di akhir Progress 4 ada pertanyaan: kita mengejar angka paper, atau cukup menjelaskan kenapa angkanya berbeda."

**Supaya paham:**

- Kartu 6 penting karena jadi jembatan ke slide berikutnya. Dosen meminta kita mencoba mengejar angka paper, dan itulah yang dikerjakan minggu ini.
- "Trace datang per menit": di data publik TT, trace muncul serempak selama 1 detik setiap kira-kira 60 detik. Jadi window 10 detik sering tidak kebagian trace sama sekali.

**Kalau ditanya:**

- *"Kenapa variasi seed bisa sebesar itu?"* Data Test di leave_event_out berisi jenis fault yang belum pernah dilihat model. Sedikit perbedaan bobot awal bisa membuat model "menebak" ke arah berbeda pada fault baru itu.

---

## Slide 3. Tindak Lanjut dari Progress 4

*Durasi: 1 menit*

**Yang diucapkan:**

"Ini status dari rencana minggu lalu.

Soal angka paper: sesuai arahan, saya menjalankan split yang dipakai di kode rilis EADRO dengan 3 seed dan 50 epoch. Ini sudah selesai, hasilnya saya tunjukkan sebentar lagi.

Soal false alarm: sebagian terjawab. Dengan split kode rilis, false alarm turun ke sekitar 6%. Tapi di split tanpa leakage masih 40 sampai 60%.

Perbandingan fusion sedang berjalan. F1 dan F2 sudah dibandingkan di dua protokol.

Window yang lebih panjang: T = 30 sudah selesai untuk within_event. T = 60 saya tunda karena butuh sekitar 7 jam dan RAM sekitar 9 GB."

**Supaya paham:**

- Warna status: hijau selesai, kuning sebagian, biru berjalan.
- F1 dan F2 di slide ini adalah nama varian fusion (F1 = fusion asli EADRO, F2 = tanpa GLU), bukan metrik F1. Kalau perlu, tegaskan ini saat bicara karena namanya mirip.

---

## Slide 4. Progress Minggu Ini

*Durasi: 45 detik*

**Yang diucapkan:**

"Pekerjaan minggu ini saya kelompokkan jadi tiga.

Pertama, mengejar angka paper: menjalankan split kode rilis, membandingkan teks paper dengan kode rilis, dan menganalisis rumus HR@k di kode rilis.

Kedua, melengkapi baseline F1: hasil di tiga protokol, efisiensi, acceptance check, dan eksperimen window T = 30.

Ketiga, perbandingan fusion F1 dan F2. F3 dan F4 masih menunggu paper rujukannya.

Urutan presentasi mengikuti tiga kelompok ini."

---

## Slide 5. Paper dan Kode Rilis EADRO Berbeda

*Durasi: 2 menit*

**Yang diucapkan:**

"Waktu mencoba mengejar angka paper, saya menemukan bahwa cara membagi data di paper dan di kode rilis EADRO ternyata berbeda.

Di sebelah kiri kutipan dari paper, bagian V.A halaman 7. Paper bilang data dari periode yang berbeda dibagi menjadi 60% training dan 40% testing. Paper tidak menyebut pembagian acak, tidak menyebut validation set, dan tidak menjelaskan cara memilih epoch.

Di sebelah kanan isi kode rilisnya. Di align.py, window digeser 1 detik. Lalu semua window diacak dengan np.random.shuffle, tanpa seed. Rasio testnya 0,3, jadi 70/30, bukan 60/40. Dan di base.py, epoch terbaik dipilih dari HR@1 di Test.

Jadi paper menyebut pembagian per periode 60/40, sedangkan kode rilis mengacak per window 70/30 dan memilih epoch memakai Test."

**Supaya paham:**

- Kenapa ini penting: kalau epoch dipilih memakai Test, nilai Test jadi terlalu optimis. Test seharusnya hanya dilihat sekali di akhir.
- "Tanpa seed" artinya pembagian data berbeda setiap kali kode dijalankan, jadi hasilnya tidak bisa diulang persis.
- Commit 03ab600 adalah versi kode di repo EADRO yang kita pakai. Disebut supaya orang lain bisa mengecek baris yang sama.

**Kalau ditanya:**

- *"Yakin kode rilis itu yang dipakai untuk hasil paper?"* Tidak bisa dipastikan 100%. Yang bisa dipastikan: kode yang dirilis penulis melakukan pembagian acak. Kalau penulis memakai kode lain untuk paper, kode itu tidak dipublikasikan.
- *"Di mana bisa dicek?"* Nomor barisnya ada di tabel, dan laporan lengkapnya di `Report/Laporan_Tingkat_A_Protokol_Asli.md` bagian 3.0.

---

## Slide 6. Menguji Split Kode Rilis

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Pertanyaannya: selisih kita dengan paper itu karena model dan datanya, atau karena cara split?

Untuk menjawabnya saya membuat protokol random_original, yang meniru split kode rilis.

Gambar atas menunjukkan bedanya. Di within_event, tiap kejadian dipotong per waktu: Train dulu, lalu Val, lalu Test, berurutan. Di random_original, window diacak, jadi Train dan Test bercampur.

Masalahnya, window yang bersebelahan isinya 9 dari 10 detik sama. Kalau satu masuk Train dan tetangganya masuk Test, model sebenarnya sudah melihat hampir seluruh isi soal ujiannya. Itu yang disebut data leakage.

Tabel di bawah merangkum: split kita membagi per waktu atau per kejadian, epoch dipilih di Val, dan tidak ada leakage. Split kode rilis mengacak per window, memilih epoch di Test, dan ada leakage."

**Supaya paham:**

- Kotak merah dan biru di baris random_original hanya ilustrasi pola acak, bukan data asli.
- "Ada jeda pemisah" di tabel: window yang melintasi batas Train/Val/Test dibuang, supaya tidak ada window yang separuh isinya di Train dan separuh di Test. Istilah teknisnya purge.

**Kalau ditanya:**

- *"Kalau tahu ada leakage, kenapa tetap dijalankan?"* Sebagai diagnosis. Kalau dengan split ini angkanya mendekati paper, berarti sebagian besar selisih datang dari cara split, bukan dari model kita yang salah.

---

## Slide 7. Hasil Split Kode Rilis vs Paper

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Ini hasilnya. Abu-abu paper, biru within_event, merah random_original.

Dengan split kode rilis, F1 jadi 0,96 dan HR@1 0,96. Paper 0,99. Selisihnya tinggal sekitar 0,02 sampai 0,03.

False alarm juga turun drastis, dari sekitar 60% jadi 5,9%.

Sisa selisih yang kecil itu masuk akal karena data publik hanya berisi 81 injeksi fault, sedangkan paper menyebut 162.

Jadi kesimpulannya, model dan pipeline kita sudah benar. Selisih besar dengan paper terutama berasal dari cara split, bukan dari implementasi."

**Supaya paham:**

- Angka random_original di grafik ini diambil dari epoch 49 (epoch terakhir). Di slide 9 angkanya lebih rendah (F1 0,923) karena di sana epoch dipilih memakai kriteria kode rilis, yang kebetulan memilih epoch awal (9 atau 19). Kalau ditanya kenapa angkanya beda antar slide, ini jawabannya.
- Ini kesimpulan paling penting dari bagian "mengejar angka paper". Sampaikan dengan yakin.

**Kalau ditanya:**

- *"Jadi angka paper itu salah?"* Bukan salah, tapi angka itu mengukur hal yang lebih mudah: model menebak window yang tetangganya sudah dia lihat waktu training. Di kondisi nyata, model harus menghadapi data yang benar-benar baru.

---

## Slide 8. Rumus HR@k di Kode Rilis Bermasalah

*Durasi: 2 menit*

**Yang diucapkan:**

"Temuan kedua ada di rumus HR@k di kode rilis.

Di base.py, window normal yang diprediksi normal ikut dihitung sebagai true positive. Lalu HR@k dihitung sebagai jumlah hit dibagi TP ditambah FN.

Masalahnya, window normal tidak punya root cause, jadi tidak mungkin menjadi hit. Tapi mereka ikut menambah penyebut. Akibatnya aneh: makin sedikit false alarm, makin banyak window normal yang benar, penyebutnya makin besar, dan HR@1 malah turun.

Di Test kita, batas atas HR@1 dengan rumus ini 0,598, sekalipun modelnya sempurna. Supaya bisa dapat HR@1 0,99 dengan Precision 0,984 seperti di paper, Test paper harus berisi paling banyak sekitar 2,6% window normal.

Karena itu, semua perbandingan setelah ini memakai metrik (std): hanya window gangguan yang dihitung, sesuai definisi HR@k yang umum."

**Supaya paham:**

- Analogi sederhana: kamu menghitung persentase pasien sakit yang diagnosisnya tepat, tapi orang sehat yang dinyatakan sehat ikut dimasukkan ke penyebut. Makin banyak orang sehat yang benar dinyatakan sehat, persentasenya malah turun. Jelas rumusnya yang salah.
- Batas 2,6% artinya: hasil paper hanya mungkin kalau Test-nya hampir tidak berisi window normal. Ini petunjuk tambahan bahwa pengaturan eksperimen paper berbeda dari yang kita kira.

**Kalau ditanya:**

- *"Metrik (std) lebih tinggi atau lebih rendah dari metrik asli?"* Biasanya lebih tinggi untuk HR@k, karena penyebutnya hanya window gangguan. Contoh baseline within_event: HR@1 asli 0,63, HR@1 (std) 0,82.

---

## Slide 9. Baseline F1 di Tiga Protokol

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Ini rangkuman baseline F1, yaitu fusion asli EADRO, di tiga protokol, semuanya pakai metrik (std).

within_event: F1 0,767 dan HR@1 0,822.
leave_event_out: F1 0,806 dan HR@1 0,650.
random_original: F1 0,923 dan HR@1 0,975, tapi protokol ini ada leakage-nya.

Dua protokol pertama mengukur hal berbeda. within_event menguji event yang sudah dikenal model. leave_event_out menguji fault baru, dan di sini lokalisasi paling sulit: HR@1 turun ke 0,65."

**Supaya paham:**

- F1 leave_event_out sedikit lebih tinggi dari within_event, padahal leave_event_out lebih sulit. Kemungkinan besar karena komposisi Test-nya berbeda: porsi window gangguan di Test leave_event_out sekitar 60%, di within_event sekitar 56%. Makin banyak window gangguan, makin mudah Precision dan F1 terlihat tinggi. Yang membedakan kesulitan secara jelas adalah HR@1.
- Angka setelah ± adalah sd antar 3 seed.

---

## Slide 10. Efisiensi Baseline F1

*Durasi: 1 menit*

**Yang diucapkan:**

"Dari sisi efisiensi, model EADRO kecil: 66 ribu parameter, 18.560 di antaranya di modul fusion. Inferensi sekitar 0,27 milidetik per window. Memori puncak 2,75 GB. Training sekitar 1,26 detik per seribu window.

Memori puncak itu didominasi data yang dimuat, bukan modelnya. Bobot modelnya sendiri cuma sekitar 0,26 MB. random_original memakai memori paling besar, 3,56 GB, karena data yang dimuatnya paling banyak."

**Supaya paham:**

- Semua angka diukur di laptop yang sama (CPU, tanpa GPU), jadi bisa dibandingkan antar run.
- Selisih inferensi di bawah 0,01 ms tidak berarti apa-apa, itu masih noise pengukuran.

---

## Slide 11. Baseline Acceptance Check

*Durasi: 1 menit*

**Yang diucapkan:**

"Ini pengecekan apakah baseline layak dipakai sebagai pembanding.

Pipeline correctness terpenuhi: tiap tahap data sudah saya verifikasi dengan fungsi asli EADRO, dan ada 7 bug di kode rilis yang saya perbaiki.

Arsitekturnya sama dengan paper.

Experimental consistency baru sebagian. Seed dan pengaturan tercatat, tapi Val di within_event kurang mewakili Test.

Training stabil. Tidak ada NaN, dan run ulang dengan seed yang sama memberi angka yang persis sama.

Performance sanity check terpenuhi. Dengan split kode rilis hasilnya mendekati paper, dan jauh di atas tebakan acak yang HR@1-nya sekitar 0,037."

**Supaya paham:**

- Tebakan acak 0,037 = 1 dibagi 27 service.
- "Val kurang mewakili Test": skor Val sekitar 0,96, tapi Test sekitar 0,82. Akibatnya epoch yang dipilih lewat Val belum tentu epoch terbaik untuk Test.
- Rincian 7 bug ada di laporan-laporan sebelumnya. Kalau ditanya detail, bilang saja rinciannya ada di laporan dan bisa ditunjukkan.

---

## Slide 12. Window T = 30

*Durasi: 2 menit*

**Yang diucapkan:**

"Sekarang eksperimen panjang window. Di Progress 4 kita membandingkan T = 5 dan T = 10. Minggu ini saya menambahkan T = 30. Pengaturannya sama persis dengan baseline: within_event, fusion F1, 3 seed, 15 epoch. Yang diubah hanya T.

Abu-abu T = 5, biru T = 10, merah T = 30.

Deteksi membaik. F1 naik dari 0,767 ke 0,844. Ini satu-satunya selisih di seluruh percobaan T yang jelas lebih besar dari variasi antar seed.

Lokalisasi hampir tidak berubah. HR@1 0,822 jadi 0,832. HR@3 naik sedikit, dari 0,883 ke 0,915.

Satu catatan: Test di T = 30 berisi window normal lebih sedikit, 12.520 dibanding 14.200. Kalau jumlahnya disamakan, Precision T = 30 sekitar 0,72. Masih lebih tinggi dari T = 10 yang 0,658."

**Supaya paham:**

- "Jelas lebih besar dari variasi seed" artinya: selang kepercayaan 95% selisih F1 adalah +0,031 sampai +0,123, tidak menyentuh nol. Metrik lain selang kepercayaannya masih menyentuh nol, jadi belum bisa dipastikan berbeda.
- Kenapa window normal lebih sedikit: window yang melintasi batas Train/Val/Test dibuang. Makin panjang window, makin banyak yang melintasi batas. Di T = 30 ada 6.960 window yang dibuang, di T = 10 hanya 2.160.
- Kenapa Precision terpengaruh: Precision dihitung dari alarm yang dibunyikan. Kalau window normalnya lebih sedikit, alarm palsunya juga lebih sedikit secara jumlah, jadi Precision terlihat lebih bagus. Makanya saya koreksi jadi sekitar 0,72.
- Error bar di grafik T = 30 kecil sekali. Artinya hasilnya stabil antar seed (sd F1 0,009 dibanding 0,017 di T = 10).

**Kalau ditanya:**

- *"Kenapa tidak langsung pakai T = 30 untuk semua eksperimen?"* Lihat slide 14: biayanya sekitar 2,4 kali waktu training, dan lokalisasinya tidak membaik. Juga belum diuji di leave_event_out.
- *"Signifikan dengan 3 seed saja?"* Untuk F1, ya, walaupun 3 seed itu sedikit. Saya pakai uji yang konservatif (Welch, derajat bebas 2). Untuk metrik lain belum.

---

## Slide 13. Trace Lebih Sering Muncul, False Alarm Turun

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Kenapa deteksi membaik? Grafik ini menunjukkan dua hal per T. Biru: persentase window yang berisi trace. Merah: false alarm di Test.

Trace di data ini datang dalam burst 1 detik setiap sekitar 60 detik. Jadi makin panjang window, makin sering trace tertangkap. Di T = 10 hanya 18% window yang berisi trace, di T = 30 hampir 50%.

Bersamaan dengan itu, false alarm turun dari 74% di T = 5, ke 62% di T = 10, lalu 47% di T = 30.

Tapi ada dua catatan. Pertama, hanya 9 service yang punya trace. Root cause dari 54 di antara 81 fault tidak punya trace sama sekali. Ini cocok dengan HR@1 yang tidak naik: untuk sebagian besar fault, trace tidak membantu menunjuk root cause.

Kedua, belum tentu perbaikannya karena trace. Window 30 detik juga berisi metrics dan log yang lebih panjang. Untuk memastikan, perlu eksperimen tanpa trace."

**Supaya paham:**

- Error bar merah di T = 5 dan T = 10 besar (sd 20 dan 14 poin persen), di T = 30 kecil (3 poin). Sekali lagi menunjukkan T = 30 lebih stabil.
- Logika kartu "Belum tentu karena trace": dua hal berubah bersamaan (trace lebih sering dan data lain lebih panjang). Kita tidak bisa bilang mana yang berpengaruh tanpa memisahkan keduanya. Eksperimen pemisahnya disebut ablasi: melatih ulang model tanpa trace, lalu melihat apakah perbaikannya hilang.

**Kalau ditanya:**

- *"Kenapa trace datang per menit?"* Sepertinya beban kerja (workload generator) di dataset ini mengirim permintaan serempak sekali per menit. Ini berbeda dari paper yang menyebut 0,2 sampai 0,5 permintaan per detik secara merata.

---

## Slide 14. Biaya Window yang Lebih Panjang

*Durasi: 1 menit*

**Yang diucapkan:**

"Perbaikan itu ada harganya. Dibanding T = 10, T = 30 butuh sekitar 2,4 kali waktu training, 3,3 kali waktu inferensi, dan 1,9 kali memori. Membangun datanya juga hampir 2 jam.

Ada satu biaya yang sering terlewat: model baru bisa memutuskan setelah 30 detik data terkumpul, bukan 10 detik. Untuk troubleshooting, itu berarti respons lebih lambat.

Parameter total naik sedikit, karena sebagian lapisan modelnya bergantung pada panjang window. Tapi parameter fusion tetap 18.560, jadi perbandingan fusion tidak terpengaruh oleh T."

**Supaya paham:**

- Inferensi naik lebih tajam dari training karena tiap window membawa data 3 kali lebih banyak.
- Baris "Keputusan setelah" bukan hasil pengukuran, tapi konsekuensi langsung dari panjang window.

---

## Slide 15. Kandidat Fusion Mechanism

*Durasi: 1 menit*

**Yang diucapkan:**

"Masuk ke bagian utama, perbandingan fusion. Ada empat kandidat.

F1 adalah fusion asli EADRO: concat, lalu FC, lalu GLU. Kategorinya gating-based. Sudah selesai di tiga protokol.

F2 adalah concat dan FC saja, tanpa GLU. Ini bisa dianggap ablasi dari EADRO. Sudah selesai di within_event dan leave_event_out.

F3 Learnable Weighted Feature Fusion, rujukannya MULAN dan Topo-MFP. F4 Cross-Attention, rujukannya FAMOS. Dua ini menunggu paper rujukannya dipelajari dulu.

Semua varian memakai data, seed, dan hyperparameter yang sama. Hanya modul fusion yang diganti."

**Supaya paham:**

- "Hanya modul fusion yang diganti" adalah syarat supaya perbandingannya adil. Kalau hal lain ikut berubah, kita tidak tahu perbedaan hasil datang dari mana.

---

## Slide 16. F1 vs F2: Apa Bedanya?

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Ini beda F1 dan F2 secara arsitektur.

Input-nya sama: tiap service punya vektor dari log 16 dimensi, metrics 64, dan traces 64. Totalnya 144 dimensi, digabung (concat).

Di F1, vektor 144 itu masuk FC jadi 128, lalu GLU menghasilkan 64.

Di F2, vektor 144 masuk FC langsung jadi 64, lalu ReLU.

GLU bekerja begini: output FC dibagi dua. Satu bagian dijadikan gate lewat sigmoid, nilainya antara 0 dan 1. Gate ini menentukan seberapa banyak bagian lain diteruskan. Jadi model bisa belajar meredam atau meloloskan informasi tertentu.

F2 punya parameter fusion separuhnya, 9.280, dan total model 14% lebih kecil.

Paper EADRO sendiri tidak menguji apakah GLU memang dibutuhkan. Jadi F2 sekaligus menjawab pertanyaan itu."

**Supaya paham:**

- Analogi GLU: seperti keran. Satu bagian membawa airnya (informasi), bagian lain mengatur seberapa lebar keran dibuka. Kerannya dipelajari sendiri oleh model.
- ReLU: fungsi sederhana yang membuat nilai negatif jadi nol. Fungsi aktivasi paling umum.
- FC (fully connected): lapisan yang mengalikan input dengan matriks bobot. Angka 144→128 artinya mengubah vektor 144 dimensi jadi 128 dimensi.

---

## Slide 17. Hasil within_event

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Hasil pertama, di within_event. Merah F1, biru F2.

F2 mengurangi false alarm. FPR turun dari 62% ke 42%, dan Recall-nya sama, 0,923. Jadi alarm palsu berkurang tanpa kehilangan gangguan yang tertangkap.

Lokalisasi setara. HR@1 0,822 dibanding 0,842, masih dalam variasi seed.

Tapi ini belum pasti. Di seed 42, F2 tidak lebih baik. Uji-t berpasangan untuk F1 memberi p sekitar 0,2, jadi belum bisa disebut berbeda nyata."

**Supaya paham:**

- Uji-t berpasangan: membandingkan F1 dan F2 pada seed yang sama, lalu melihat apakah selisihnya konsisten. p ≈ 0,2 artinya ada sekitar 20% kemungkinan selisih sebesar ini muncul hanya karena kebetulan. Biasanya batasnya 5%.
- Perbaikan Precision terlihat di grafik (0,658 ke 0,736). Itulah yang membuat F1 naik.

---

## Slide 18. Hasil leave_event_out

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Di leave_event_out, ceritanya berbeda.

False alarm F2 tetap turun, dari 59% ke 38%, dan itu terjadi di ketiga seed.

Tapi lebih banyak fault yang terlewat. Recall turun dari 0,938 ke 0,884, jadi F1 hanya naik 0,02.

Dan yang paling penting, lokalisasi turun. HR@1 dari 0,650 ke 0,509, dan turunnya terjadi di ketiga seed.

Jadi pada fault yang belum pernah dilihat, menghapus GLU membuat model lebih sering salah menunjuk root cause."

**Supaya paham:**

- Ini kebalikan dari within_event. Di event yang dikenal, F2 sedikit lebih baik. Di fault baru, F2 jelas lebih buruk untuk lokalisasi.
- "Di ketiga seed" penting karena variasi seed di protokol ini besar. Kalau arahnya sama di tiga seed, hasilnya lebih bisa dipercaya.

---

## Slide 19. GLU Membantu Lokalisasi pada Fault Baru

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Slide ini memperkuat temuan tadi. Grafik menunjukkan HR@1 di Test per seed, pada tiap epoch yang dievaluasi. Merah F1, biru F2.

Polanya konsisten. Di setiap seed, epoch terbaik F2 masih di bawah epoch terburuk F1. Jadi ini bukan soal salah pilih epoch.

Ini juga bukan efek dari deteksi. Kalau dihitung hanya dari fault yang berhasil terdeteksi, HR@1 tetap turun dari 0,69 ke 0,57.

Dan perbedaannya hanya muncul pada event baru. Di Val, yang berisi event yang sudah dikenal, HR@1 keduanya sama, sekitar 0,76 sampai 0,94.

Jadi kesimpulan saya, GLU tidak berpengaruh pada event yang dikenal, tapi membantu lokalisasi pada gangguan yang belum pernah dilihat."

**Supaya paham:**

- "Bukan efek deteksi": HR@1 (std) menghitung fault yang tidak terdeteksi sebagai gagal. Karena Recall F2 lebih rendah, HR@1-nya otomatis ikut turun. Untuk memastikan penurunannya bukan cuma karena itu, HR@1 dibagi Recall. Hasilnya tetap turun, jadi F2 memang lebih buruk dalam menunjuk root cause.
- Kenapa titik di grafik tidak lengkap di semua epoch: kode hanya menghitung Test ketika skor Val membaik. Itu disengaja supaya Test tidak dipakai untuk memilih apa pun.
- Dugaan kenapa GLU membantu (belum dibuktikan): gate bisa belajar meredam modalitas yang menyesatkan. Pada fault baru, kemampuan memilih informasi itu lebih berguna. Kalau ditanya, bilang ini masih dugaan.

---

## Slide 20. Efisiensi F1 vs F2

*Durasi: 1 menit*

**Yang diucapkan:**

"Dari sisi efisiensi: F2 punya parameter fusion separuh F1, dan total 14% lebih kecil. Tapi waktu per epoch, waktu inferensi, dan memorinya praktis sama.

Artinya model lebih kecil, tapi tidak lebih cepat. Waktu komputasi didominasi oleh encoder, GAT, dan pemuatan data, bukan oleh modul fusion.

Satu catatan pengukuran: waktu F2 within_event saya ambil dari seed 123 saja, karena dua seed lainnya berjalan waktu laptop memakai baterai."

**Supaya paham:**

- Laptop dengan baterai menurunkan kecepatan CPU, jadi waktu yang terukur saat itu tidak bisa dibandingkan dengan run lain.
- GAT (graph attention network): bagian model yang memproses hubungan antar 27 service sebagai graf.

---

## Slide 21. Kesimpulan F1 vs F2

*Durasi: 1,5 menit*

**Yang diucapkan:**

"Kesimpulan perbandingan F1 dan F2.

Di within_event, F2 sedikit lebih baik untuk deteksi, lokalisasinya setara.

Di leave_event_out, deteksi seimbang, tapi F1 lebih baik untuk lokalisasi, HR@1 selisih 0,14.

Ada tiga poin. F2 mengurangi false alarm sekitar 20 poin persen di kedua protokol. GLU penting untuk fault baru: tanpa GLU, root cause lebih sering salah ditunjuk. Dan F2 lebih kecil tapi tidak lebih cepat.

Karena hasilnya berbeda arah di dua protokol, saya mengusulkan leave_event_out sebagai protokol utama. Protokol inilah yang bisa membedakan mekanisme fusion, dan paling mirip kondisi nyata."

**Supaya paham:**

- Pesan utamanya: kesimpulan tentang fusion bergantung pada protokol. Kalau hanya memakai within_event, kita akan menyimpulkan GLU tidak perlu, dan itu menyesatkan.

---

## Slide 22. Keterbatasan

*Durasi: 1 menit*

**Yang diucapkan:**

"Beberapa keterbatasan yang perlu saya sampaikan.

Pertama, baru 3 seed. Variasi HR@1 antar seed di leave_event_out sekitar 0,1, sebesar efek yang sedang dicari.

Kedua, Val kurang mewakili Test. Di within_event, skor Val sekitar 0,96 tapi Test 0,82.

Ketiga, false alarm masih tinggi, 40 sampai 60% di split tanpa leakage.

Keempat, waktu hanya diukur sekali per run, jadi peka terhadap kondisi laptop.

Kelima, analisis per jenis fault dan per service belum dilakukan.

Keenam, F2 belum dijalankan di random_original. Ini akan dijalankan setelah semua varian fusion siap."

---

## Slide 23. Rencana Berikutnya

*Durasi: 1 menit*

**Yang diucapkan:**

"Rencana berikutnya.

Prioritas pertama, implementasi F3 dan F4 setelah paper rujukannya dipelajari, lalu menjalankannya di within_event dan leave_event_out dengan 3 seed. Estimasinya sekitar 1,7 jam per varian.

Untuk window: menjalankan T = 30 di leave_event_out, sekitar 2 jam, dan ablasi tanpa trace di T = 10 dan T = 30, untuk memastikan apakah perbaikan di T = 30 memang karena trace. Ablasi ini perlu opsi baru di kode.

Lalu semua varian di random_original, seed tambahan sampai total 5, dan benchmark efisiensi dari checkpoint dalam kondisi yang sama.

T = 60 dipertimbangkan di akhir, karena butuh sekitar 7 jam dan RAM sekitar 9 GB.

Dan usulan saya: leave_event_out menjadi protokol utama untuk kesimpulan fusion."

**Supaya paham:**

- Benchmark dari checkpoint: model yang sudah dilatih disimpan, lalu waktu inferensinya diukur ulang semua sekaligus di kondisi laptop yang sama. Tidak perlu melatih ulang.
- Usulan di bagian akhir sebaiknya dijadikan pertanyaan ke dosen secara lisan, misalnya: "Apakah Bapak/Ibu setuju dengan usulan ini?"

**Kalau ditanya:**

- *"Kenapa T = 60 ditaruh terakhir?"* Biayanya paling besar, dan di T = 30 lokalisasi tidak membaik. Lalu di T = 60 komposisi label berubah cukup banyak (window normal di celah antar fault berkurang hampir separuh), jadi hasilnya lebih sulit ditafsirkan.

---

## Slide 24. Terimakasih

*Durasi: 10 detik*

**Yang diucapkan:**

"Sekian dari saya. Terima kasih, Bapak/Ibu. Saya persilakan kalau ada pertanyaan atau masukan."

---

## Pertanyaan umum yang mungkin muncul

**"Jadi kenapa hasil kita jauh dari paper?"**
Penyebab utamanya cara split. Paper kemungkinan memakai split yang mirip kode rilis, yaitu acak per window. Split seperti itu bocor karena window bersebelahan hampir identik. Dengan split itu, hasil kita 0,96, dekat dengan paper 0,99. Rumus HR@k di kode rilis juga bermasalah.

**"Kenapa tidak pakai split kode rilis saja supaya angkanya bagus?"**
Karena angkanya tidak mencerminkan kemampuan model menghadapi data baru. Untuk membandingkan mekanisme fusion secara jujur, kita perlu split tanpa leakage.

**"Bedanya within_event dan leave_event_out apa, dalam satu kalimat?"**
within_event: model diuji pada bagian akhir dari kejadian yang awalnya sudah dia lihat. leave_event_out: model diuji pada jenis fault yang sama sekali belum pernah dia lihat.

**"Kenapa hanya 3 seed?"**
Satu run sekitar 15 sampai 33 menit tergantung T dan protokol, dan training jalan di laptop tanpa GPU. 3 seed itu batas minimum untuk melihat variasi. Seed tambahan sudah ada di rencana.

**"Apa kontribusi proyek ini?"**
Ada tiga temuan yang bisa diklaim. Pertama, selisih besar dengan paper berasal dari cara split dan rumus HR@k di kode rilis. Kedua, GLU membantu lokalisasi pada fault baru, dan efek ini tidak terlihat kalau hanya memakai within_event. Ketiga, window yang lebih panjang memperbaiki deteksi tapi tidak lokalisasi, dengan biaya komputasi yang besar.

---

## Kalau waktunya mepet

Untuk presentasi 15 sampai 20 menit:

- Slide 2 dan 3 cukup 30 detik masing-masing. Sebut poin utamanya saja.
- Slide 10, 11, dan 20 cukup dibacakan kesimpulan di callout bawahnya.
- Slide 14 cukup satu kalimat: "Biayanya sekitar 2,4 kali waktu training dan keputusan tertunda 30 detik."
- Slide 16 cukup jelaskan bahwa F2 adalah F1 tanpa GLU, lalu langsung ke hasil.

Slide yang jangan dipersingkat: 5, 7, 18, 19, dan 21. Di situlah temuan utamanya.
