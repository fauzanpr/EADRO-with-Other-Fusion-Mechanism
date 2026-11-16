# Script Presentasi Progress 6

Pasangan dari `PPT Progress/Progress 6 Ringkas.pptx` (14 slide). Dibuat 17 November 2026.

Perkiraan waktu: 15 sampai 18 menit.

Tiap slide berisi:

- **Yang diucapkan.** Tidak perlu dihafal persis. Yang penting urutannya.
- **Supaya paham.** Untuk kamu sendiri, tidak perlu diucapkan.
- **Kalau ditanya.** Hanya untuk slide yang kemungkinan besar ditanya.

---

## Istilah singkat

Baca ini dulu sebelum latihan.

- **Window**: potongan data sepanjang T detik. T = 10 berarti satu window berisi 10 detik log, metrics, dan trace. Window digeser per 1 detik, jadi window yang bersebelahan isinya hampir sama.
- **Fault dan root cause**: fault adalah gangguan yang sengaja disuntikkan. Root cause adalah service tempat gangguan itu disuntikkan. Ada 27 service.
- **Dua tugas model**: deteksi (ada gangguan atau tidak) dan lokalisasi (service mana root cause-nya).
- **Train, Val, Test**: Train untuk belajar, Val untuk memilih epoch terbaik, Test untuk nilai akhir.
- **Split**: cara membagi data ke Train, Val, dan Test.
  - `within_event`: tiap kejadian dipotong per waktu. Awalnya untuk Train, akhirnya untuk Test. Model diuji pada kejadian yang sudah ia kenal.
  - `leave_event_out`: jenis fault tertentu disimpan khusus untuk Test. Model diuji pada fault yang belum pernah ia lihat.
  - Split kode rilis: semua window diacak lalu dibagi 70/30.
- **Data leakage**: isi data Test bocor ke Train, jadi nilai Test terlalu bagus.
- **F1-score**: nilai deteksi, gabungan dari Precision dan Recall.
- **HR@1**: seberapa sering root cause yang benar ada di urutan pertama tebakan model.
- **False alarm**: window normal yang salah dianggap gangguan.
- **Seed**: angka awal untuk proses acak. Seed berbeda menghasilkan model yang sedikit berbeda. Kita pakai 3 seed lalu dirata-rata.
- **Fusion**: cara menggabungkan log, metrics, dan trace jadi satu. F1 adalah fusion asli EADRO (dengan GLU), F2 adalah F1 tanpa GLU.

---

## Slide 1. Progress 6

*15 detik*

**Yang diucapkan:**

"Selamat pagi, Bapak/Ibu. Saya akan menyampaikan Progress 6 dari replikasi EADRO dan perbandingan fusion di dataset Train Ticket."

---

## Slide 2. Review Progress Sebelumnya

*45 detik*

**Yang diucapkan:**

"Singkatnya, di progress sebelumnya ada tiga hal.

Pertama, hasil baseline kita jauh dari paper. F1-score 0,77 dan HR@1 0,82, sedangkan paper melaporkan 0,99.

Kedua, false alarm-nya banyak. Sekitar 60% window normal ikut dianggap gangguan.

Ketiga, arahan dari Bapak/Ibu waktu itu adalah mencoba mengejar angka di paper."

**Supaya paham:**

Angka 0,77 dan 0,82 adalah hasil split `within_event`. Kalau ditanya angka `leave_event_out`, ada di slide 5.

---

## Slide 3. Yang Dikerjakan Minggu Ini

*30 detik*

**Yang diucapkan:**

"Minggu ini ada tiga pekerjaan.

Pertama, mencari tahu kenapa hasil kita jauh dari paper.
Kedua, mencoba window yang lebih panjang, T = 30.
Ketiga, membandingkan fusion F1 dengan F2, yaitu F1 tanpa GLU. F3 dan F4 masih menunggu paper rujukan."

---

## Slide 4. Kenapa Hasil Kita Jauh dari Paper?

*2 menit*

**Yang diucapkan:**

"Waktu saya bandingkan isi paper dengan kode yang dirilis penulisnya, ternyata cara membagi datanya berbeda.

Di paper, data dibagi per periode waktu, 60% untuk training dan 40% untuk testing.

Tapi di kode rilis, semua window diacak dulu, lalu dibagi 70/30. Epoch terbaik juga dipilih memakai data Test.

Bedanya bisa dilihat di gambar. Split kita membagi berurutan: Train dulu, lalu Val, lalu Test. Split kode rilis mengacak semuanya, jadi Train dan Test bercampur.

Masalahnya, window yang bersebelahan isinya hampir sama. Window detik 1 sampai 10 dan window detik 2 sampai 11 sama 9 detiknya. Kalau satu masuk Train dan tetangganya masuk Test, model sebenarnya sudah melihat isi data Test waktu training. Itu yang disebut data leakage."

**Supaya paham:**

- Kalimat yang dikutip ada di paper bagian V.A halaman 7.
- Pembagian acak ada di `align.py` baris 133 sampai 138 (pakai `np.random.shuffle`, tanpa seed). Rasio 70/30 di baris 174. Pemilihan epoch pakai Test ada di `base.py` baris 101 sampai 105.
- Memilih epoch pakai Test itu masalah karena Test seharusnya hanya dilihat sekali di akhir. Kalau dipakai untuk memilih, nilainya jadi terlalu optimis.

**Kalau ditanya:**

- *"Yakin kode itu yang dipakai untuk paper?"* Tidak bisa dipastikan. Yang pasti, kode yang dirilis penulis melakukan pembagian acak. Kalau penulis memakai kode lain, kode itu tidak dipublikasikan.
- *"Buktinya di mana?"* Nomor barisnya di atas, dan penjelasan lengkapnya ada di `Report/Laporan_Tingkat_A_Protokol_Asli.md` bagian 3.0.

---

## Slide 5. Hasil Baseline di Tiga Cara Split

*1,5 menit*

**Yang diucapkan:**

"Untuk membuktikannya, saya menjalankan baseline dengan split kode rilis, lalu membandingkannya dengan split kita.

Dengan split kode rilis, F1-score 0,92 dan HR@1 0,98. Itu sudah dekat dengan paper yang 0,99. Jadi model dan pipeline kita sudah benar. Selisih besar dengan paper terutama datang dari cara split.

Dua split kita mengukur hal yang berbeda. within_event menguji kejadian yang sudah dikenal model, HR@1-nya 0,82. leave_event_out menguji fault yang belum pernah dilihat, dan di sini HR@1 turun ke 0,65. Ini paling mirip kondisi nyata.

Satu temuan lagi: rumus HR@k di kode rilis keliru. Window normal ikut dihitung, padahal window normal tidak punya root cause. Jadi semua hasil di sini saya hitung ulang dengan rumus standar."

**Supaya paham:**

- Sisa selisih kecil dengan paper (0,92 vs 0,99) masuk akal karena data publik hanya berisi 81 injeksi fault, sedangkan paper menyebut 162.
- Soal rumus HR@k: di kode rilis, window normal yang ditebak benar ikut masuk ke penyebut, padahal tidak mungkin masuk ke pembilang. Analoginya: menghitung persentase pasien sakit yang diagnosisnya tepat, tapi orang sehat ikut dimasukkan ke penyebut. Makin banyak orang sehat yang benar dinyatakan sehat, persentasenya malah turun.
- F1-score `leave_event_out` (0,81) sedikit lebih tinggi dari `within_event` (0,77), padahal lebih sulit. Kemungkinan karena porsi window gangguan di Test-nya lebih besar. Perbedaan tingkat kesulitan terlihat jelas di HR@1.

**Kalau ditanya:**

- *"Kenapa tidak pakai split kode rilis saja supaya angkanya bagus?"* Karena angka itu tidak menunjukkan kemampuan model menghadapi data baru. Untuk membandingkan fusion secara jujur, kita perlu split tanpa leakage.

---

## Slide 6. Baseline Acceptance Check

*1 menit*

**Yang diucapkan:**

"Ini pengecekan apakah baseline sudah layak jadi pembanding.

Pipeline sudah benar. Tiap tahap saya cek dengan fungsi asli EADRO, dan ada 7 bug di kode rilis yang saya perbaiki.

Arsitekturnya sama dengan paper.

Experimental consistency baru sebagian. Seed dan pengaturan sudah tercatat, tapi nilai Val lebih tinggi dari Test, jadi Val belum sepenuhnya mewakili Test.

Training stabil. Tidak ada NaN, dan kalau dijalankan ulang dengan seed yang sama, hasilnya persis sama.

Dan dengan split kode rilis, hasilnya mendekati paper."

**Supaya paham:**

- "Nilai Val lebih tinggi dari Test": di `within_event`, skor Val sekitar 0,96 sedangkan Test sekitar 0,82.
- Rincian 7 bug ada di laporan-laporan sebelumnya. Kalau ditanya detail, bilang rinciannya ada di laporan.

---

## Slide 7. Mencoba Window T = 30

*1,5 menit*

**Yang diucapkan:**

"Berikutnya window yang lebih panjang. Sebelumnya kita sudah mencoba T = 5 dan T = 10. Sekarang saya tambahkan T = 30. Pengaturan lainnya sama.

Deteksi membaik. F1-score naik dari 0,77 ke 0,84, dan false alarm turun dari 62% ke 47%.

Tapi lokalisasi tidak berubah. HR@1 tetap sekitar 0,83. Ini masuk akal, karena root cause dari 54 di antara 81 fault memang tidak punya trace sama sekali.

Dan biayanya besar. Training 2,4 kali lebih lama, dan model baru bisa memutuskan setelah data 30 detik terkumpul."

**Supaya paham:**

- Alasan mencoba T = 30: trace di data ini datang sekali per menit, selama 1 detik. Di T = 10 hanya sekitar 18% window yang kebagian trace. Di T = 30 jadi sekitar 50%.
- Kenaikan F1-score ini satu-satunya perbedaan di percobaan T yang jelas lebih besar dari variasi antar seed.
- Belum tentu perbaikannya karena trace. Window 30 detik juga berisi metrics dan log yang lebih panjang. Untuk memastikannya perlu uji tanpa trace (ada di rencana).

**Kalau ditanya:**

- *"Kenapa tidak pakai T = 30 untuk semua eksperimen?"* Biayanya 2,4 kali lebih besar, lokalisasinya tidak membaik, dan belum diuji di `leave_event_out`.
- *"T = 60 kapan?"* Dipertimbangkan di akhir. Butuh sekitar 7 jam dan RAM sekitar 9 GB.

---

## Slide 8. Beda Fusion F1 dan F2

*1 menit*

**Yang diucapkan:**

"Masuk ke perbandingan fusion. Tiap service punya data log, metrics, dan trace yang digabung jadi 144 angka.

Di F1, gabungan itu masuk ke lapisan FC, lalu ke GLU. Di F2, GLU-nya diganti ReLU biasa.

GLU bekerja begini: output FC dibagi dua. Bagian pertama membawa informasi, bagian kedua mengatur seberapa banyak informasi itu diteruskan. Jadi model bisa belajar meredam informasi yang kurang berguna.

Paper EADRO tidak pernah menguji apakah GLU memang dibutuhkan. Karena itu F2 saya buat tanpa GLU."

**Supaya paham:**

- Analogi GLU: seperti keran. Satu bagian adalah airnya, bagian lain mengatur seberapa lebar keran dibuka. Lebar keran itu dipelajari sendiri oleh model.
- ReLU: fungsi sederhana yang membuat nilai negatif jadi nol.
- FC (fully connected): lapisan yang mengubah ukuran vektor dengan mengalikannya dengan bobot.

---

## Slide 9. Hasil F1 vs F2

*1,5 menit*

**Yang diucapkan:**

"Ini hasilnya. Merah F1 dengan GLU, biru F2 tanpa GLU. Kiri within_event, kanan leave_event_out.

Pada kejadian yang sudah dikenal, hasil keduanya hampir sama.

Pada fault baru, bedanya terlihat. Tanpa GLU, root cause lebih sering salah ditunjuk. HR@1 turun dari 0,65 ke 0,51.

Tapi ada sisi baiknya juga. F2 punya false alarm lebih sedikit di kedua split, turun sekitar 20 poin persen."

**Supaya paham:**

- False alarm `within_event`: 62% ke 42%. `leave_event_out`: 59% ke 38%.
- Di `within_event`, F1-score F2 sedikit lebih tinggi (0,82 vs 0,77), tapi belum bisa disebut berbeda nyata dengan 3 seed. Makanya di slide ditulis "hampir sama".
- Di `leave_event_out`, F2 juga lebih banyak melewatkan fault (Recall 0,94 ke 0,88), jadi F1-score-nya hanya naik sedikit.

---

## Slide 10. GLU Membantu pada Fault Baru

*1 menit*

**Yang diucapkan:**

"Untuk memastikan hasil tadi bukan kebetulan, ini HR@1 per seed di setiap epoch yang dievaluasi.

Polanya konsisten. Di ketiga seed, hasil terbaik F2 masih di bawah hasil terburuk F1.

Penurunannya juga bukan cuma karena F2 lebih banyak melewatkan fault. Kalau hanya menghitung fault yang berhasil terdeteksi, HR@1 F2 tetap lebih rendah, 0,57 dibanding 0,69.

Jadi GLU memang membantu menunjuk root cause pada fault yang belum pernah dilihat."

**Supaya paham:**

- Kenapa titik di grafik tidak lengkap di semua epoch: Test hanya dihitung ketika nilai Val membaik. Ini disengaja supaya Test tidak dipakai untuk memilih apa pun.
- Kenapa GLU membantu masih dugaan: mungkin karena GLU bisa meredam modalitas yang menyesatkan, dan kemampuan itu lebih berguna pada fault baru. Kalau ditanya, sampaikan sebagai dugaan, bukan fakta.

---

## Slide 11. Efisiensi F1 vs F2

*45 detik*

**Yang diucapkan:**

"Dari sisi efisiensi, F2 punya parameter fusion separuh F1, dan total parameternya 14% lebih kecil.

Tapi waktu training, waktu inferensi, dan memorinya praktis sama. Sebagian besar waktu habis di encoder dan GAT, bukan di bagian fusion. Jadi F2 lebih kecil, tapi tidak lebih cepat."

**Supaya paham:**

- GAT (graph attention network): bagian model yang memproses hubungan antar 27 service sebagai graf.
- Selisih inferensi 0,27 vs 0,28 ms terlalu kecil untuk berarti apa-apa.

---

## Slide 12. Kesimpulan

*1 menit*

**Yang diucapkan:**

"Kesimpulannya ada tiga.

Pertama, selisih besar dengan paper sebagian besar karena cara split di kode rilis, bukan karena model kita.

Kedua, window T = 30 membuat deteksi lebih baik, tapi lokalisasi tidak berubah, dan biayanya jauh lebih besar.

Ketiga, GLU tidak terlalu berpengaruh pada kejadian yang sudah dikenal, tapi membantu menemukan root cause pada fault baru.

Semua hasil ini baru dari 3 seed, jadi masih perlu dikonfirmasi dengan seed tambahan."

---

## Slide 13. Rencana Berikutnya

*1 menit*

**Yang diucapkan:**

"Rencana berikutnya: implementasi F3 dan F4 setelah paper rujukannya dipelajari, lalu menjalankannya di dua split. Setelah itu menambah seed jadi 5.

Untuk window, saya ingin menguji model tanpa trace di T = 10 dan T = 30, supaya tahu apakah perbaikan di T = 30 memang karena trace. Lalu T = 30 di leave_event_out, dan T = 60 di akhir kalau waktunya cukup.

Usulan saya, leave_event_out dijadikan acuan utama untuk membandingkan fusion, karena di split inilah perbedaan F1 dan F2 terlihat. Apakah Bapak/Ibu setuju?"

**Supaya paham:**

- Kalimat terakhir sengaja dibuat jadi pertanyaan, supaya dosen memberi keputusan.
- "Perlu opsi baru di kode": `main.py` belum punya pilihan untuk mematikan satu modalitas, jadi harus ditambahkan dulu.

---

## Slide 14. Terimakasih

*10 detik*

**Yang diucapkan:**

"Sekian dari saya. Terima kasih, Bapak/Ibu. Saya persilakan kalau ada pertanyaan atau masukan."

---

## Pertanyaan yang mungkin muncul

**"Jadi angka paper itu salah?"**
Bukan salah, tapi angka itu mengukur hal yang lebih mudah. Dengan split acak, model menebak window yang tetangganya sudah ia lihat waktu training.

**"Bedanya within_event dan leave_event_out dalam satu kalimat?"**
within_event menguji model pada akhir kejadian yang awalnya sudah ia lihat. leave_event_out menguji model pada jenis fault yang sama sekali belum pernah ia lihat.

**"Kenapa cuma 3 seed?"**
Training jalan di laptop tanpa GPU, satu run sekitar 15 sampai 33 menit. 3 seed batas minimum untuk melihat variasi. Seed tambahan sudah ada di rencana.

**"F1 di slide itu metrik atau fusion?"**
Di deck ini, metrik selalu ditulis "F1-score". "F1" dan "F2" tanpa "-score" adalah nama varian fusion.
