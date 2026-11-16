# Laporan Eksperimen: Baseline EADRO dengan 3 Seed (Train Ticket)

| | |
|---|---|
| Tanggal eksperimen | 10 November 2026, 00.38–02.13 WIB (total 94 menit 40 detik) |
| Dijalankan oleh | Pengguna sendiri, di laptop (CPU saja) |
| Model | EADRO asli (fusion `concat_glu`), tanpa perubahan arsitektur |
| Data | Train Ticket (TT) saja, `A1`, jendela T = 10 detik |
| Skema data | `within_event` dan `leave_event_out` |
| Seed | 42, 7, 123 |
| Jumlah run | 6 (2 skema × 3 seed), semuanya selesai tanpa kegagalan |
| Alasan eksperimen | Saran dosen: pakai 3 seed berbeda, supaya hasil baseline punya rata-rata dan simpangan, bukan satu angka |

---

## 1. Ringkasan

1. **Baseline belum mendekati angka paper, di kedua skema.** Pada skema yang paling realistis (`leave_event_out`), HR@1 hanya 0,650 ± 0,099 dan F1 0,806 ± 0,036. Paper melaporkan 0,990 dan 0,989. Selisihnya jauh di luar rentang ketidakpastian 3 seed.
2. **Yang lemah adalah alarm palsu dan lokalisasi, bukan deteksi gangguan.** Recall 0,92–0,94, jadi gangguan jarang terlewat. Tetapi dari perhitungan turunan (bagian 6.2), sekitar 60% jendela normal di Test salah ditandai sebagai gangguan. Itulah yang menekan Precision ke 0,66–0,71.
3. **Seed mengubah hasil lokalisasi cukup besar pada `leave_event_out`.** HR@1 berkisar 0,566 sampai 0,759 hanya karena ganti seed. Pada `within_event` jauh lebih stabil (0,799 sampai 0,857).
4. **Dengan 3 seed, perbedaan kecil antar varian fusion tidak akan terdeteksi di `leave_event_out`.** Selang kepercayaan 95% untuk HR@1 selebar ±0,25. Untuk membandingkan fusion, `within_event` lebih layak, atau jumlah seed harus ditambah (bagian 8).
5. **Pemilihan epoch lewat Val tidak bisa diandalkan.** Terutama di `within_event`, Val nyaris datar antar epoch dan Val jauh lebih optimistis daripada Test.

---

## 2. Tujuan dan pertanyaan

Sebelum ini baseline hanya punya **satu** angka per skema (seed 42). Satu angka tidak memberi tahu apakah hasilnya kebetulan bagus atau jelek. Eksperimen ini menjawab:

1. Berapa rata-rata dan simpangan baku (sd) performa EADRO jika hanya seed yang diganti?
2. Apakah baseline mendekati angka paper?
3. Seberapa besar variasi antar seed dibandingkan efek yang nanti ingin dideteksi (perbedaan antar mekanisme fusion)?

**Seed** adalah bilangan awal untuk pengacak. Ia menentukan nilai awal bobot model dan urutan data yang dimasukkan per batch. Ganti seed berarti model mulai dari titik awal lain, sehingga hasil akhirnya bisa berbeda.

---

## 3. Rancangan eksperimen

### 3.1 Yang dijaga tetap sama di semua run

| Pengaturan | Nilai |
|---|---|
| Arsitektur | EADRO asli: encoder per modalitas (log, metrik, trace), `concat → FC → GLU`, GATv2, 27 service |
| Fusion | `concat_glu` |
| Jumlah parameter | 66.050 total, 18.560 di modul fusion |
| Epoch | 15 |
| Batch | 256 |
| Learning rate | 0,001 |
| `alpha` | 0,5 |
| `patience` | 10 (tidak menghentikan run mana pun: semua run menyelesaikan 15 epoch) |
| Panjang jendela T | 10 detik, stride 1 |
| Kernel konvolusi | trace [2], metrik [2], hidden 64 |
| `self_attn` | aktif |
| Evaluasi | tiap 5 epoch (setelah epoch 4, 9, 14) |
| Kriteria pilih epoch | `combo` = (F1(std) + HR@1(std)) / 2 pada Val |
| Perangkat | CPU (i7-8650U). `params.json` mencatat `gpu: true`, tetapi log menyatakan "Using CPU...": tidak ada GPU yang dipakai |

### 3.2 Yang berubah

Hanya dua hal: **skema data** dan **seed**. Pembagian data (isi train/val/test) **tetap** untuk semua seed. Artinya variasi yang kita ukur hanya berasal dari inisialisasi dan urutan batch, **bukan** dari pembagian data yang berbeda (lihat keterbatasan di bagian 7).

### 3.3 Dua skema data

| | `within_event` | `leave_event_out` |
|---|---|---|
| Cara membagi | Tiap kejadian gangguan dipotong menurut waktu: 50% awal train, 10% berikut val, 40% akhir test | 27 kejadian gangguan utuh ditahan untuk Val/Test; model tidak pernah melihatnya saat latihan |
| Pertanyaan yang dijawab | Bisakah model mengenali gangguan yang sudah sebagian ia lihat? | Bisakah model mengenali gangguan yang belum pernah ia lihat? |
| Tingkat kesulitan | Lebih mudah | Lebih realistis dan lebih sulit |

Tidak ada detik yang dipakai bersama antar bagian (dipurge per detik).

| Bagian | `within_event`: total / gangguan / normal | `leave_event_out`: total / gangguan / normal |
|---|---|---|
| Train | 40.510 / 24.823 / 15.687 | 46.160 / 30.029 / 16.131 |
| Val | 7.490 / 5.084 / 2.406 | 7.695 / 2.388 / 5.307 |
| Test | 32.190 / 17.990 / 14.200 | 27.352 / 16.452 / 10.900 |

Perhatikan Val `leave_event_out`: 69% normal. Di Test hanya 40%. Ini penting untuk membaca Precision (bagian 6.2).

### 3.4 Cara menjalankan

```bash
# dari folder proyek; hasil di work/result/<hash>/
nohup systemd-inhibit --what=sleep:idle --who="EADRO grid" \
  bash -c 'pipeline/run_grid.sh leave_event_out 15 "42 7 123" "concat_glu" \
        && pipeline/run_grid.sh within_event 15 "42 7 123" "concat_glu"' \
  > train_grid3seed.out 2>&1 &
```

Run yang sudah selesai dicatat di `work/result/grid_selesai.txt` dan dilewati bila skrip dijalankan ulang.

### 3.5 Daftar run

| Skema | Seed | Hash | Mulai–selesai | Lama | Detik/epoch | Epoch terpilih |
|---|---|---|---|---|---|---|
| `leave_event_out` | 42 | `97e94b9a` | 00.38–00.55 | 17 m 02 s | 58,7 | 14 |
| `leave_event_out` | 7 | `a8af9989` | 00.55–01.12 | 16 m 27 s | 58,7 | 14 |
| `leave_event_out` | 123 | `9e7dfa9a` | 01.12–01.28 | 16 m 16 s | 58,0 | 9 |
| `within_event` | 42 | `fb3e4cc0` | 01.28–01.43 | 14 m 51 s | 51,0 | 14 |
| `within_event` | 7 | `74f2db5a` | 01.43–01.58 | 14 m 56 s | 51,1 | 14 |
| `within_event` | 123 | `dc38d8d0` | 01.58–02.13 | 14 m 50 s | 50,7 | 9 |

Efisiensi (sama di semua run): 0,26–0,27 ms per jendela saat inferensi; memori puncak 2.752–2.788 MB.

---

## 4. Cara membaca metrik

Setiap jendela 10 detik adalah satu contoh. Contoh itu berlabel **gangguan** (ada service yang kena fault) atau **normal**. Model menjawab dua hal: "ada gangguan?" dan "service mana biangnya?".

Kode asli EADRO menghitung F1, Recall, Precision dengan menghitung jendela normal yang ditebak benar sebagai "benar positif". HR@k dibagi dengan jumlah jendela gangguan **ditambah** jendela normal yang benar. Akibatnya angka asli bercampur antara dua kelas. Pada kode kita ditambahkan versi **`(std)`** yang lebih baku:

| Metrik `(std)` | Arti | Rumus (di `Eadro/codes/base.py`) |
|---|---|---|
| **Recall** | Dari semua jendela gangguan, berapa yang terdeteksi | `tp_faulty / n_faulty` |
| **Precision** | Dari semua jendela yang diberi alarm, berapa yang benar-benar gangguan | `tp_faulty / (tp_faulty + FP)` |
| **F1** | Rata-rata harmonik Precision dan Recall | `2·tp / (2·tp + FP + FN)` |
| **HR@k** | Dari semua jendela gangguan, berapa yang service biangnya masuk k tebakan teratas | `hit@k / n_faulty` |
| **NDCG@k** | Seperti HR@k tetapi memberi nilai lebih bila biang ada di peringkat atas | idem |

Dua hal yang perlu diingat:

- **Gangguan yang lolos (dianggap normal) dihitung sebagai gagal di HR@k.** Jadi HR@1 tidak mungkin melebihi Recall.
- Jendela normal hanya memengaruhi Precision dan F1 (lewat FP). Karena itu **Precision bergantung pada proporsi normal** di data, sedangkan Recall dan HR@k tidak.

Tabel utama di bawah memakai `(std)`. Versi asli diberikan di bagian 5.4 untuk perbandingan dengan paper.

---

## 5. Hasil

Semua angka adalah **Test pada epoch yang dipilih** oleh kriteria `combo` di Val.

### 5.1 Per seed

**`leave_event_out`**

| Metrik (std) | seed 42 | seed 7 | seed 123 |
|---|---|---|---|
| Epoch terpilih | 14 | 14 | 9 |
| F1 | 0,766 | 0,835 | 0,816 |
| Recall | 0,874 | 0,952 | 0,990 |
| Precision | 0,681 | 0,744 | 0,694 |
| HR@1 | 0,566 | 0,624 | 0,759 |
| HR@3 | 0,691 | 0,704 | 0,868 |
| HR@5 | 0,741 | 0,733 | 0,888 |
| NDCG@3 | 0,639 | 0,672 | 0,825 |
| NDCG@5 | 0,660 | 0,684 | 0,833 |

**`within_event`**

| Metrik (std) | seed 42 | seed 7 | seed 123 |
|---|---|---|---|
| Epoch terpilih | 14 | 14 | 9 |
| F1 | 0,786 | 0,758 | 0,757 |
| Recall | 0,881 | 0,946 | 0,943 |
| Precision | 0,710 | 0,632 | 0,632 |
| HR@1 | 0,809 | 0,857 | 0,799 |
| HR@3 | 0,865 | 0,911 | 0,873 |
| HR@5 | 0,872 | 0,924 | 0,892 |
| NDCG@3 | 0,842 | 0,889 | 0,843 |
| NDCG@5 | 0,845 | 0,894 | 0,851 |

### 5.2 Rata-rata ± sd, rentang, dan selang kepercayaan

sd memakai pembagi n−1 (sampel). Selang kepercayaan (SK) 95% memakai distribusi t dengan 2 derajat kebebasan (t = 4,303), dihitung dari angka per seed di atas yang dibulatkan 3 desimal. Batas atas yang melebihi 1 hanya menunjukkan selang yang sangat lebar; metriknya sendiri tidak bisa lebih dari 1.

**`leave_event_out`**

| Metrik (std) | Rata-rata ± sd | Min–maks | SK 95% | Paper |
|---|---|---|---|---|
| F1 | 0,806 ± 0,036 | 0,766–0,835 | 0,717–0,894 | 0,989 |
| Recall | 0,938 ± 0,059 | 0,874–0,990 | 0,792–1,086 | 0,995 |
| Precision | 0,707 ± 0,033 | 0,681–0,744 | 0,624–0,789 | 0,984 |
| HR@1 | 0,650 ± 0,099 | 0,566–0,759 | 0,404–0,896 | 0,990 |
| HR@3 | 0,754 ± 0,099 | 0,691–0,868 | 0,509–0,999 | 0,992 |
| HR@5 | 0,788 ± 0,087 | 0,733–0,888 | 0,571–1,004 | 0,993 |
| NDCG@3 | 0,712 ± 0,099 | 0,639–0,825 | 0,465–0,959 | 0,994 |
| NDCG@5 | 0,726 ± 0,094 | 0,660–0,833 | 0,493–0,958 | 0,994 |

**`within_event`**

| Metrik (std) | Rata-rata ± sd | Min–maks | SK 95% | Paper |
|---|---|---|---|---|
| F1 | 0,767 ± 0,017 | 0,757–0,786 | 0,726–0,808 | 0,989 |
| Recall | 0,923 ± 0,037 | 0,881–0,946 | 0,832–1,014 | 0,995 |
| Precision | 0,658 ± 0,045 | 0,632–0,710 | 0,546–0,770 | 0,984 |
| HR@1 | 0,822 ± 0,031 | 0,799–0,857 | 0,745–0,899 | 0,990 |
| HR@3 | 0,883 ± 0,024 | 0,865–0,911 | 0,822–0,944 | 0,992 |
| HR@5 | 0,896 ± 0,027 | 0,872–0,924 | 0,831–0,961 | 0,993 |
| NDCG@3 | 0,858 ± 0,027 | 0,842–0,889 | 0,791–0,925 | 0,994 |
| NDCG@5 | 0,864 ± 0,027 | 0,845–0,894 | 0,797–0,930 | 0,994 |

### 5.3 Dibandingkan paper

Nilai paper (TT) ada di kolom terakhir tabel di atas. Pembacaannya:

- **F1, Precision, HR@1, NDCG@3, NDCG@5: angka paper di luar SK 95%** di kedua skema. Selisih rata-ratanya 0,13–0,34 (terbesar: HR@1 `leave_event_out`, 0,34). HR@3 dan HR@5 di `within_event` juga di luar SK (selisih 0,10–0,11).
- **HR@3 dan HR@5 di `leave_event_out`, serta Recall di kedua skema:** angka paper **masuk** SK. Itu bukan bukti baseline kita sama dengan paper. Itu hanya berarti, dengan 3 seed, SK-nya terlalu lebar untuk menolak kemiripan. Selisih rata-ratanya tetap 0,06–0,24.
- Karena paper tidak menyebut nilai T atau skema pembagian datanya, perbandingan ini adalah **indikasi**, bukan uji replikasi yang ketat.

### 5.4 Versi metrik asli kode (untuk disandingkan dengan paper)

Paper memakai kode rilis, sehingga angkanya kemungkinan dihitung dengan definisi asli yang mencampur kelas normal. Kami tidak tahu pasti. Karena itu kedua versi diberikan; keduanya sama-sama jauh dari paper.

> **Pembaruan 16 November 2026:** dugaan di paragraf ini dibantah oleh `Laporan_Tingkat_A_Protokol_Asli.md` (bagian 5.3). Dengan rumus HR@k asli, batas atas HR@1 di data kita hanya sekitar 0,60. HR@1 0,990 di paper hanya mungkin bila Test paper hampir tanpa jendela normal. Bandingkan HR@k dengan paper memakai versi (std).

| Metrik (asli) | `leave_event_out` | `within_event` | Paper |
|---|---|---|---|
| F1 | 0,842 ± 0,032 | 0,813 ± 0,029 | 0,989 |
| HR@1 | 0,513 ± 0,093 | 0,634 ± 0,064 | 0,990 |
| HR@3 | 0,595 ± 0,098 | 0,681 ± 0,068 | 0,992 |
| HR@5 | 0,622 ± 0,092 | 0,692 ± 0,073 | 0,993 |

### 5.5 Dua skema dibandingkan

| | `leave_event_out` | `within_event` | Selisih (within − leave) | SK 95% selisih* |
|---|---|---|---|---|
| HR@1 | 0,650 | 0,822 | +0,172 | −0,086 sampai +0,430 |
| F1 | 0,806 | 0,767 | −0,039 | −0,136 sampai +0,059 |
| Precision | 0,707 | 0,658 | −0,048 | −0,187 sampai +0,091 |

\* Konservatif (t dengan 2 derajat kebebasan, galat baku Welch).

**Tidak satu pun selisih ini pasti berbeda dari nol dengan hanya 3 seed.** Arahnya sesuai dugaan (lokalisasi lebih mudah bila model pernah melihat bagian gangguan yang sama), tetapi buktinya belum cukup untuk dinyatakan sebagai temuan.

---

## 6. Analisis

### 6.1 Seberapa besar variasi seed

| Metrik (std) | sd `leave_event_out` | sd `within_event` | Koefisien variasi (sd/rata-rata) L / W |
|---|---|---|---|
| F1 | 0,036 | 0,017 | 4% / 2% |
| Precision | 0,033 | 0,045 | 5% / 7% |
| HR@1 | 0,099 | 0,031 | 15% / 4% |

- Variasi **terbesar** ada di lokalisasi `leave_event_out` (HR@1 bergerak 0,19 antar seed). Pada skema ini model harus menebak service biang untuk kejadian yang belum pernah dilihat, jadi titik awal yang berbeda bisa membawa ke tebakan yang cukup berbeda.
- Variasi **terkecil** ada di F1 `within_event` (sd 0,017).
- Seed 123 `leave_event_out` memberi HR@1 0,759, jauh di atas dua seed lain (0,566; 0,624). Dengan n = 3 kami tidak bisa memastikan itu hasil bagus yang kebetulan atau sifat sebenarnya dari model. Itulah alasan perlu lebih banyak seed.

### 6.2 Deteksi: alarm palsu, bukan gangguan yang lolos

Log hanya mencatat Recall dan Precision. Dari keduanya dan jumlah jendela di `split_summary.json` kita bisa **menurunkan** tingkat alarm palsu (FPR), yaitu persentase jendela normal yang ditandai gangguan:

```
TP  = Recall(std) × jumlah jendela gangguan
FP  = TP × (1 / Precision(std) − 1)
FPR = FP / jumlah jendela normal
```

Ini perkiraan turunan (Precision dibulatkan 3 desimal), bukan angka yang dicatat langsung oleh kode.

| Skema | Bagian | seed 42 | seed 7 | seed 123 | Rata-rata |
|---|---|---|---|---|---|
| `leave_event_out` | Val | 0,546 | 0,623 | 0,570 | **0,580** |
| `leave_event_out` | Test | 0,616 | 0,494 | 0,659 | **0,590** |
| `within_event` | Val | 0,094 | 0,128 | 0,080 | **0,101** |
| `within_event` | Test | 0,455 | 0,699 | 0,694 | **0,616** |

Pembacaan:

1. **Sekitar 60% jendela normal di Test salah dialarm**, di kedua skema. Recall tinggi (0,92–0,94), tetapi dibayar dengan alarm berlebihan. Model hampir "selalu curiga".
2. **Precision terlihat lumayan (0,66–0,71) hanya karena jendela gangguan mendominasi Test (56–60%).** Jika proporsi normal lebih besar, Precision akan turun lebih jauh.
3. **Di `leave_event_out`, Precision Val (0,42–0,47) jauh lebih rendah daripada Test (0,68–0,74), tetapi FPR keduanya sama (≈ 0,58).** Selisih Precision berasal dari proporsi normal: 69% di Val, 40% di Test. Ini menjawab teka-teki lama mengapa Val tampak "lebih sulit" untuk Precision.
4. **Di `within_event`, FPR Val hanya 0,10 sedangkan Test 0,62.** Jendela normal di Val jauh lebih mudah daripada di Test. *Penyebab belum diverifikasi.* Dugaan yang konsisten dengan diagnosis lama (`diagnose_alarm.py` pada run 9df622b8): sebagian jendela normal di Test adalah jendela di celah sekitar gangguan dan data tanpa-fault, yang sulit dibedakan oleh model.

### 6.3 Pemilihan epoch

Val dievaluasi di epoch 4, 9, 14. Test hanya dihitung bila Val `combo` membaik, sehingga sebagian epoch tidak punya angka Test.

**Val combo per epoch yang dievaluasi**

| Skema | Seed | Epoch 4 | Epoch 9 | Epoch 14 | Terpilih |
|---|---|---|---|---|---|
| `leave_event_out` | 42 | 0,686 | 0,721 | **0,738** | 14 |
| `leave_event_out` | 7 | 0,715 | 0,705 | **0,761** | 14 |
| `leave_event_out` | 123 | 0,733 | **0,767** | 0,761 | 9 |
| `within_event` | 42 | 0,929 | 0,908 | **0,943** | 14 |
| `within_event` | 7 | 0,942 | 0,925 | **0,950** | 14 |
| `within_event` | 123 | 0,942 | **0,948** | 0,943 | 9 |

Temuan:

- **`within_event`: Val combo hanya bergerak 0,91–0,95.** Beda antar epoch kecil dibanding selisih Val–Test, sehingga pilihan epoch hampir arbitrer. Contoh nyata: pada seed 7, HR@1(std) Test adalah 0,806 di epoch 4 dan 0,857 di epoch 14. Selisih 0,05 itu sama besar dengan sd antar seed.
- **Pada `leave_event_out` seed 42, Val dan Test tidak sepakat urutan epoch.** Val memilih epoch 14, tetapi Test HR@1 pada epoch 9 (0,621) lebih tinggi daripada epoch 14 (0,566).
- **Epoch terpilih sering yang terakhir (14 dari 15).** Artinya 15 epoch mungkin terlalu pendek. Loss pelatihan masih turun di akhir (0,06–0,10), tetapi apakah itu berarti Test ikut membaik belum diuji.

### 6.4 Deteksi vs lokalisasi

Dua tahap EADRO punya sumber kegagalan berbeda:

| Tahap | Indikator | Kondisi |
|---|---|---|
| Deteksi: gangguan terdeteksi? | Recall 0,92–0,94 | Baik |
| Deteksi: tidak alarm palsu? | FPR ≈ 0,60 | **Buruk** |
| Lokalisasi: biang tepat di peringkat 1 | HR@1 0,65 (L) / 0,82 (W) | Sedang; sangat bergantung seed di L |
| Lokalisasi: biang di 5 teratas | HR@5 0,79 (L) / 0,90 (W) | Cukup |

Selisih HR@5 − HR@1 (0,14 di L, 0,07 di W) berarti sekitar 40% dari kesalahan HR@1 adalah kasus "nyaris benar": biang ada di peringkat 2–5. Sisanya (±60%) biang di luar 5 teratas atau gangguannya tidak terdeteksi sama sekali.

---

## 7. Keterbatasan

1. **Hanya 3 seed.** Rata-rata dan sd dari 3 titik sendiri sangat tidak pasti. SK 95% selebar ±2,5 sd. Kami melaporkan sd apa adanya, tetapi mohon baca sebagai ukuran kasar.
2. **Seed hanya mengubah inisialisasi dan urutan batch.** Pembagian data tetap. Variasi akibat memilih kejadian gangguan yang berbeda untuk Val/Test tidak terukur, padahal bisa lebih besar. Untuk itu diperlukan validasi silang antar kejadian.
3. **Hanya 15 epoch.** Dipilih agar tiap run ±15 menit. Epoch terpilih sering yang terakhir, jadi hasil bisa berubah dengan pelatihan lebih panjang. Run lama 50 epoch (seed 42) memberi F1(std) 0,764 / HR@1(std) 0,808 di `within_event`, masih dalam rentang 3 seed ini; di `leave_event_out` run 30 epoch memberi HR@1(std) 0,539, sedikit di bawah rentang.
4. **Kriteria pilih epoch berbeda dari run lama** (`combo` vs HR@1 asli), dan jadwal evaluasi berbeda (tiap 5 epoch). Jadi angka ini **jangan** digabung dalam satu tabel dengan hasil lama.
5. **Test hanya dihitung saat Val membaik,** sehingga tidak ada kurva Test lengkap. Kami melaporkan Test pada epoch pilihan Val (tanpa mengintip Test), dan tidak bisa melaporkan "epoch terbaik di Test".
6. **Reprodusibilitas seed belum penuh.** Dengan seed 42 yang sama, loss epoch 1–4 identik dengan run lama, tetapi epoch 5 berbeda karena jadwal evaluasi berbeda. Dugaan: evaluasi memakai pembangkit acak yang sama dengan pemuat data. *Belum diverifikasi.* Akibatnya `eval_every` harus sama untuk semua varian fusion dan semua seed.
7. **Dugaan yang belum diverifikasi:** sumber FPR tinggi di Test `within_event` (bagian 6.2 butir 4) dan penyebab Val lebih mudah daripada Test untuk lokalisasi di `leave_event_out` (HR@1 Val 0,87–0,94 vs Test 0,57–0,76).
8. **Data publik TT yang kami pakai hanya 81 injeksi** (paper melaporkan 162 injeksi untuk TT). Selisih dengan paper bisa sebagian berasal dari data, bukan dari kode. SN sengaja di luar cakupan.
9. **Trace di data kita berupa lonjakan tiap ±60 detik,** sehingga dengan T = 10 hanya ±15% jendela memuat sedikitnya satu span untuk sebuah service ber-trace (±18% untuk setidaknya satu service). Ini bisa membatasi informasi trace dan belum dikaji dengan T berbeda.

---

## 8. Yang boleh dan tidak boleh disimpulkan

| Boleh dikatakan | Tidak boleh dikatakan |
|---|---|
| Baseline kami belum mendekati angka paper; selisihnya jauh melebihi variasi antar seed | "Replikasi gagal karena kode salah" (penyebab belum dipastikan; data, T, dan pembagian data bisa berbeda) |
| Variasi seed bisa sebesar 0,19 pada HR@1 di `leave_event_out` | "`within_event` lebih baik dari `leave_event_out`" sebagai fakta mutlak (SK selisih mencakup nol) |
| Deteksi lemah terutama karena alarm palsu (≈ 60% jendela normal) | "Model gagal mendeteksi gangguan" (Recall 0,92–0,94) |
| Pemilihan epoch lewat Val kurang andal | "Epoch 14 selalu terbaik" |
| Perbandingan fusion butuh banyak seed dan harus melaporkan mean ± sd | Menyatakan satu varian fusion lebih baik dari selisih < 0,1 pada HR@1 (L) dengan 3 seed |

### Berapa seed yang dibutuhkan?

Perkiraan kasar (pendekatan normal, dua kelompok sama besar, daya 80%, α = 0,05, memakai sd dari 3 seed ini sehingga sendirinya tidak pasti):

| Selisih HR@1 yang ingin dideteksi | Seed per varian di `leave_event_out` (sd ≈ 0,10) | Seed per varian di `within_event` (sd ≈ 0,03) |
|---|---|---|
| 0,10 | ±15 | 2 |
| 0,05 | ±60 | ±6 |

Dengan kata lain, `leave_event_out` tidak cocok untuk membedakan varian fusion yang selisihnya kecil. Desain berpasangan (seed yang sama di semua varian) kemungkinan mengurangi kebutuhan ini, tetapi belum diukur.

---

## 9. Langkah berikutnya

1. **Eksplorasi T** (saran kedua dosen): T ∈ {5, 10, 30, 60} dengan 3 seed, pada skema yang sama. Analisis cakupan span per T sudah ada sebagai dasar.
2. **Tentukan skema untuk perbandingan fusion.** Usul: `within_event` untuk perbandingan utama (variasi kecil), `leave_event_out` sebagai uji generalisasi dengan seed lebih banyak.
3. **Tambah seed** (misalnya 5) bila akan membandingkan fusion.
4. **Selidiki alarm palsu:** uraikan FPR per jenis jendela normal (celah vs tanpa-fault), dan uji normalisasi per run.
5. **Epoch lebih panjang** (30–50) pada satu skema untuk melihat apakah epoch akhir benar-benar lebih baik di Test.
6. **Putuskan kriteria pilih epoch** sebelum menjalankan varian fusion, dan tetapkan `--eval_every` yang sama untuk semuanya.

---

## Lampiran A. Nilai per epoch yang dievaluasi

Format: Val(combo / F1(std) / Pre(std) / HR@1(std)) dan Test(F1(std) / Pre(std) / HR@1(std)). "—" berarti Test tidak dihitung karena Val tidak membaik.

| Skema | Seed | Epoch | Val combo | Val F1 | Val Pre | Val HR@1 | Test F1 | Test Pre | Test HR@1 |
|---|---|---|---|---|---|---|---|---|---|
| `leave_event_out` | 42 | 4 | 0,686 | 0,535 | 0,371 | 0,838 | 0,774 | 0,655 | 0,524 |
| `leave_event_out` | 42 | 9 | 0,721 | 0,536 | 0,367 | 0,905 | 0,786 | 0,657 | 0,621 |
| `leave_event_out` | 42 | 14 | 0,738 | 0,607 | 0,443 | 0,869 | 0,766 | 0,681 | 0,566 |
| `leave_event_out` | 7 | 4 | 0,715 | 0,555 | 0,385 | 0,876 | 0,840 | 0,727 | 0,651 |
| `leave_event_out` | 7 | 9 | 0,705 | 0,505 | 0,339 | 0,904 | — | — | — |
| `leave_event_out` | 7 | 14 | 0,761 | 0,584 | 0,415 | 0,937 | 0,835 | 0,744 | 0,624 |
| `leave_event_out` | 123 | 4 | 0,733 | 0,612 | 0,446 | 0,855 | 0,835 | 0,746 | 0,674 |
| `leave_event_out` | 123 | 9 | 0,767 | 0,612 | 0,441 | 0,922 | 0,816 | 0,694 | 0,759 |
| `leave_event_out` | 123 | 14 | 0,761 | 0,632 | 0,474 | 0,890 | — | — | — |
| `within_event` | 42 | 4 | 0,929 | 0,947 | 0,936 | 0,910 | 0,788 | 0,689 | 0,806 |
| `within_event` | 42 | 9 | 0,908 | 0,940 | 0,974 | 0,877 | — | — | — |
| `within_event` | 42 | 14 | 0,943 | 0,953 | 0,956 | 0,933 | 0,786 | 0,710 | 0,809 |
| `within_event` | 7 | 4 | 0,942 | 0,970 | 0,967 | 0,913 | 0,774 | 0,655 | 0,806 |
| `within_event` | 7 | 9 | 0,925 | 0,930 | 0,900 | 0,920 | — | — | — |
| `within_event` | 7 | 14 | 0,950 | 0,957 | 0,941 | 0,942 | 0,758 | 0,632 | 0,857 |
| `within_event` | 123 | 4 | 0,942 | 0,957 | 0,926 | 0,927 | 0,755 | 0,618 | 0,813 |
| `within_event` | 123 | 9 | 0,948 | 0,971 | 0,963 | 0,924 | 0,757 | 0,632 | 0,799 |
| `within_event` | 123 | 14 | 0,943 | 0,960 | 0,953 | 0,925 | — | — | — |

## Lampiran B. Loss pelatihan

| Skema | Seed | Loss epoch 1 | Loss epoch 15 |
|---|---|---|---|
| `leave_event_out` | 42 | 1,505 | 0,066 |
| `leave_event_out` | 7 | 1,410 | 0,061 |
| `leave_event_out` | 123 | 1,517 | 0,062 |
| `within_event` | 42 | 1,648 | 0,081 |
| `within_event` | 7 | 1,635 | 0,097 |
| `within_event` | 123 | 1,679 | 0,092 |

Loss turun konsisten dan tidak ada tanda pelatihan gagal pada satu pun seed.

## Lampiran C. Berkas terkait

| Isi | Lokasi (relatif ke folder proyek) |
|---|---|
| Log per epoch | `work/result/<hash>/running.log` |
| Parameter run | `work/result/<hash>/params.json` |
| Ringkasan grid | `train_grid3seed.out`, `work/result/grid_selesai.txt` |
| Ringkasan pembagian data | `work/chunks/A1/<skema>/split_summary.json` |
| Skrip grid dan latih | `pipeline/run_grid.sh`, `pipeline/run_train.sh` |
| Definisi metrik | `Eadro/codes/base.py` (fungsi `evaluate`) |
| Dokumen terkait | `Report/Penjelasan_EDA_dan_Baseline.md` |
