# Laporan Eksperimen: Tingkat A, Meniru Protokol Kode Rilis EADRO (Train Ticket)

| | |
|---|---|
| Tanggal eksperimen | 16 November 2026, 00.48–04.08 WIB (total 3 jam 19 menit 53 detik) |
| Dijalankan oleh | Pengguna sendiri, di laptop (CPU saja) |
| Model | EADRO asli (fusion `concat_glu`), tanpa perubahan arsitektur |
| Data | Train Ticket (TT) saja, `A1`, jendela T = 10 detik, 12 run (9 berfault + 3 tanpa fault) |
| Skema data | `random_original` (baru): tiruan pembagian data di kode asli |
| Seed training | 42, 7, 123 (seed pembagian data tetap 0) |
| Jumlah run | 3, semuanya selesai 50 epoch tanpa kegagalan dan tanpa early stop |
| Alasan eksperimen | Target tugas adalah mendekati angka paper. Eksperimen ini menguji apakah selisih baseline kita ke paper berasal dari protokol evaluasi |

---

## 1. Ringkasan

1. **Dengan protokol kode asli, angka kita hampir menyamai paper.** Di epoch terakhir yang dievaluasi (49): F1(std) 0,964 ± 0,001, Precision(std) 0,961, HR@1(std) 0,963. F1 versi asli 0,978. Paper TT: F1 0,989, Precision 0,984, HR@1 0,990.
2. **Selisih besar ke paper ternyata berasal dari protokol, bukan dari model.** Model, data, dan hiperparameter sama dengan baseline sebelumnya. Yang diganti hanya cara membagi data. F1(std) naik dari 0,77–0,81 menjadi 0,96, dan HR@1(std) dari 0,65–0,82 menjadi 0,96–0,98.
3. **Alarm palsu hampir hilang.** Jendela normal yang salah dialarm turun dari sekitar 60% (protokol adil) menjadi 5,9% ± 1,4% (epoch 49).
4. **Protokol kode asli bocor waktu.** Jendela dibagi acak, sehingga hampir setiap jendela test punya tetangga di train yang berbagi 9 dari 10 detiknya. Model cukup mengingat, bukan menggeneralisasi. Karena itu angka tingkat A **bukan** ukuran kemampuan model yang adil.
5. **Metrik HR@k di kode asli cacat.** Rumusnya menghitung jendela normal yang benar sebagai pembagi. Makin sedikit alarm palsu, HR@1 asli justru makin **turun**: 0,637 di epoch 9 menjadi 0,590 di epoch 49, padahal model makin baik. Batas atasnya pada data ini hanya 0,598. Konsekuensinya, angka HR@1 0,990 di paper tidak mungkin dihasilkan rumus ini, kecuali Test paper hampir tidak berisi jendela normal (bagian 5.3).

---

## 2. Tujuan dan pertanyaan

Baseline 3 seed (`Laporan_Eksperimen_Seed.md`) memberi F1(std) 0,77–0,81 dan HR@1(std) 0,65–0,82, jauh dari paper (0,99). Dosen meminta kita tetap mengejar angka paper. Sebelum mengubah model, perlu diketahui dulu dari mana selisih itu datang.

Pertanyaan:

1. Jika kita memakai **cara membagi dan memilih epoch yang sama dengan kode asli**, apakah angka paper tercapai?
2. Apa yang terjadi pada alarm palsu, yang selama ini menjadi kelemahan utama?
3. Apakah metrik versi asli bisa dibandingkan langsung dengan paper?

---

## 3. Rancangan eksperimen

### 3.0 Teks paper vs kode rilis: dua protokol yang berbeda

Istilah "protokol asli" di laporan ini berarti **protokol kode rilis EADRO**, bukan protokol yang ditulis di paper. Keduanya berbeda.

**Teks paper** (Bagian V.A *Data Collection*, halaman 7, kolom kanan, paragraf terakhir sebelum "B. Baselines"):

> "In this way, we collect two datasets (TT and SN) with 48,296 and 126,384 traces, respectively. **Data produced in different periods are divided into training (60%) data and testing (40%) data, respectively.** The data divisions share similar distributions in abnormal/normal ratios and root causes."

Kata *random* atau *shuffle* tidak pernah dipakai paper untuk pembagian data. Kata "random" hanya muncul untuk *Random Walk*, *Random Forest*, dan cara menyuntik gangguan ("*randomly drop network packets*"). Paper juga tidak menyebut validation set atau cara memilih epoch.

**Kode rilis** (repo `Eadro/`, commit asli `03ab600`; nomor baris mengacu ke versi itu, lihat dengan `git show 03ab600:<berkas>`):

1. Jendela bergeser 1 detik: `codes/preprocess/align.py`, fungsi `get_basic`, baris 23–24:
   ```python
   intervals = [(s, s+chunk_lenth-1)
                for s in range(start, end-chunk_lenth+1)]
   ```
2. Pembagian acak per jendela, tanpa seed: `codes/preprocess/align.py`, fungsi `split_chunks`, baris 133–138:
   ```python
   train_num = int((1 - test_ratio) * chunk_num)
   test_num = int(test_ratio * chunk_num)
   np.random.shuffle(chunk_idx)

   train_idx = chunk_idx[:train_num]
   test_idx = chunk_idx[train_num:train_num+test_num]
   ```
3. Rasio 70/30 (bukan 60/40): `codes/preprocess/align.py`, baris 174:
   ```python
   parser.add_argument("--test_ratio", default=0.3, type=float)
   ```
4. Tidak ada Val; epoch dipilih memakai HR@1 asli di **Test**, dievaluasi tiap 10 epoch: `codes/base.py`, fungsi `fit`, baris 101–105:
   ```python
   if (epoch+1) % evaluation_epoch == 0:
       test_results = self.evaluate(test_loader, datatype="Test")
       if test_results["HR@1"] > best_hr1:
           best_hr1, eval_res, coverage = test_results["HR@1"], test_results, epoch
           best_state = copy.deepcopy(self.model.state_dict())
   ```
   dengan `run(evaluation_epoch=10)` di `codes/main.py` baris 75 dan `--epoches` default 50 di baris 33.

| | Teks paper | Kode rilis | `random_original` kita |
|---|---|---|---|
| Cara bagi | Per periode waktu | Acak per jendela | Acak per jendela |
| Rasio train/test | 60/40 | 70/30 | 70/30 |
| Validation set | Tidak disebut | Tidak ada; epoch dipilih pakai Test | Val = salinan Test |
| Seed pembagian | Tidak disebut | Tidak ada | `--split-seed 0` |

`random_original` meniru **kode rilis**. Pembagian per waktu yang paling dekat dengan teks paper adalah `within_event` kita (50/10/40 per wilayah fault). Mana yang sebenarnya dipakai untuk angka paper tidak bisa dipastikan dari paper maupun repo.

### 3.1 Tiga protokol yang dibandingkan

| Aspek | Kode asli EADRO (`align.split_chunks`, `base.fit`) | Tiruan kita: `random_original` | Protokol adil kita (`within_event`, `leave_event_out`) |
|---|---|---|---|
| Pembagian | Semua jendela diacak, 70% train / 30% test | **Sama** | Per blok waktu (within) atau per kejadian fault (leave) |
| Purge perbatasan | Tidak ada | **Sama** (0 jendela dibuang) | Ada: tidak ada detik yang dipakai bersama antar bagian |
| Validation set | Tidak ada, epoch dipilih dari test | **Sama**: `chunk_val` adalah salinan `chunk_test` | Val terpisah |
| Kriteria pilih epoch | HR@1 asli | **Sama** (`--select_metric HR@1`) | `combo` = (F1(std) + HR@1(std)) / 2 |
| Evaluasi | Tiap 10 epoch, 50 epoch | **Sama** (`--eval_every 10`, ep 9/19/29/39/49) | Tiap 5 epoch, 15 epoch |
| Seed pengacakan pembagian | Tidak ada (berubah tiap kali dijalankan) | `--split-seed 0`, agar bisa diulang | – |

Satu-satunya penyimpangan yang disengaja adalah seed pengacakan. Kode asli tidak memberi seed, jadi pembagiannya tidak bisa diulang persis.

### 3.2 Yang dijaga tetap sama dengan baseline

Arsitektur, fusion `concat_glu`, 66.050 parameter (18.560 di fusion), batch 256, learning rate 0,001, `patience` 10, T = 10 detik dengan stride 1, `self_attn` aktif, dan perangkat CPU i7-8650U. Fitur (cache metrik, trace, log) sama persis dengan baseline. Hanya pembagiannya yang baru.

### 3.3 Isi pembagian data

Dibangun oleh `pipeline/build_chunks_split.py --scheme random_original` (log: `work/build_logs/split_random_original.log`).

| Bagian | Total | Gangguan | Normal | % gangguan |
|---|---|---|---|---|
| Train | 57.644 | 34.575 | 23.069 | 60,0% |
| Val (= Test) | 24.705 | 14.779 | 9.926 | 59,8% |
| Test | 24.705 | 14.779 | 9.926 | 59,8% |

Total 82.349 jendela unik. Satu jendela tidak terpakai karena pembulatan ke bawah saat menghitung 70% dan 30%, sama seperti kode asli. Semua 27 service punya contoh gangguan di train (1.236–1.337 jendela) dan di test (493–594 jendela).

Bandingkan dengan `within_event`: di sana jendela normal Test sebagian besar berasal dari 40% akhir run tanpa fault (sumber drift). Di sini jendela normal tersebar acak dari semua run dan semua waktu, dan tetangganya ada di train.

### 3.4 Cara menjalankan

```bash
# dari folder proyek
work/envs/preproc38/bin/python -I pipeline/build_chunks_split.py \
    --work-dir work --name A1 --scheme random_original \
    2>&1 | tee work/build_logs/split_random_original.log

nohup systemd-inhibit --what=sleep:idle --why="EADRO tingkat A" \
    pipeline/run_grid.sh random_original 50 "42 7 123" "concat_glu" \
    --select_metric HR@1 --eval_every 10 \
    > train_randomA.out 2>&1 &

work/envs/train312/bin/python pipeline/rekap_seed.py work/result
```

### 3.5 Daftar run

| Seed | Hash | Mulai–selesai | Lama | Detik/epoch (rata-rata) | Epoch terpilih (HR@1 asli) | Loss ep 1 → ep 50 |
|---|---|---|---|---|---|---|
| 42 | `1c9748d6` | 00.48–01.58 | 70 m 09 s | 79,2 | 9 | 1,453 → 0,060 |
| 7 | `9b5849e6` | 01.58–03.03 | 64 m 28 s | 72,8 | 9 | 1,367 → 0,048 |
| 123 | `2f3b3cca` | 03.03–04.08 | 65 m 13 s | 73,1 | 19 | 1,509 → 0,049 |

Efisiensi sama di semua run: 0,27 ms per jendela saat inferensi; memori puncak 3.562–3.565 MB. Memori lebih tinggi daripada baseline (sekitar 2.780 MB) karena train lebih besar dan Val/Test dimuat dua kali. Detik per epoch seed 42 lebih lambat di 19 epoch pertama (sekitar 90 s, kemudian 72 s), kemungkinan karena laptop sedang dipakai; tidak memengaruhi hasil.

---

## 4. Hasil

Karena Val adalah salinan Test, nilai Test tersedia di **semua** epoch evaluasi, tidak hanya di epoch terpilih (berbeda dengan baseline). Hasil disajikan dengan dua aturan pemilihan epoch:

- **Kriteria asli**: epoch dengan HR@1 asli tertinggi, persis seperti kode asli.
- **Epoch terakhir (49)**: aturan tetap yang tidak bergantung pada metrik.

### 4.1 Rata-rata ± sd (n = 3), dibandingkan paper dan protokol adil

| Metrik (std) | Tingkat A, kriteria asli (ep 9/9/19) | Tingkat A, ep 49 | Paper TT | `within_event` | `leave_event_out` |
|---|---|---|---|---|---|
| F1 | 0,923 ± 0,009 | **0,964 ± 0,001** | 0,989 | 0,767 ± 0,017 | 0,806 ± 0,036 |
| Precision | 0,873 ± 0,007 | **0,961 ± 0,008** | 0,984 | 0,658 ± 0,045 | 0,707 ± 0,033 |
| Recall | 0,980 ± 0,012 | 0,966 ± 0,011 | 0,995 | 0,923 ± 0,037 | 0,938 ± 0,059 |
| HR@1 | **0,975 ± 0,014** | 0,963 ± 0,013 | 0,990 | 0,822 ± 0,031 | 0,650 ± 0,099 |
| HR@3 | 0,979 ± 0,012 | 0,966 ± 0,010 | 0,992 | 0,883 ± 0,024 | 0,754 ± 0,099 |
| HR@5 | 0,979 ± 0,012 | – | 0,993 | 0,896 ± 0,027 | 0,788 ± 0,087 |
| NDCG@3 | 0,978 ± 0,013 | – | 0,994 | 0,858 ± 0,027 | 0,712 ± 0,099 |
| Alarm palsu (FPR, turunan) | 0,213 | **0,059 ± 0,014** | – | 0,616 | 0,590 |

Kolom protokol adil diambil dari `Laporan_Eksperimen_Seed.md` (15 epoch, kriteria `combo`). FPR dihitung dengan cara yang sama seperti laporan itu (bagian 6.2): `FP = Recall × n_gangguan × (1/Precision − 1)`, `FPR = FP / n_normal`.

### 4.2 Metrik versi asli kode

| Metrik (asli) | Tingkat A, kriteria asli | Tingkat A, ep 49 | Paper TT |
|---|---|---|---|
| F1 | 0,949 ± 0,006 | **0,978 ± 0,001** | 0,989 |
| HR@1 | 0,638 ± 0,007 | 0,590 ± 0,011 | 0,990 |
| HR@3 | 0,641 ± 0,005 | – | 0,992 |

F1 asli mendekati paper. HR@1 asli sangat jauh, dan justru turun ketika model membaik. Penyebabnya dibahas di bagian 5.3.

### 4.3 Perkembangan per epoch (rata-rata 3 seed)

| Epoch | F1(std) | Precision(std) | Recall(std) | HR@1(std) | FPR | F1 asli | HR@1 asli |
|---|---|---|---|---|---|---|---|
| 9 | 0,921 | 0,870 | 0,978 | 0,972 | 0,218 | 0,947 | **0,637** |
| 19 | 0,930 | 0,897 | 0,966 | 0,963 | 0,165 | 0,955 | 0,617 |
| 29 | 0,945 | 0,912 | 0,981 | 0,978 | 0,141 | 0,965 | 0,620 |
| 39 | 0,956 | 0,951 | 0,961 | 0,959 | 0,073 | 0,973 | 0,591 |
| 49 | **0,964** | **0,961** | 0,966 | 0,963 | **0,059** | **0,978** | 0,590 |

Nilai per seed ada di Lampiran A.

---

## 5. Analisis

### 5.1 Selisih ke paper adalah efek protokol

Hanya satu hal yang berubah dibanding baseline: cara membagi data. Akibatnya:

| | Protokol adil (dua skema) | Tingkat A (ep 49) | Paper |
|---|---|---|---|
| F1(std) | 0,77–0,81 | 0,96 | 0,99 |
| HR@1(std) | 0,65–0,82 | 0,96 | 0,99 |
| FPR | ≈ 0,60 | 0,06 | – |

Lebih dari 85% selisih F1 ke paper tertutup hanya dengan mengganti protokol. Ini sangat menguatkan dugaan bahwa angka 0,99 di paper dicapai dengan pembagian acak per jendela seperti di kode rilisnya.

Kenapa pembagian acak membuat tugas begitu mudah? Jendela bertumpuk dengan stride 1 detik. Jendela yang mulai di detik t dan t+1 berbagi 9 dari 10 detik. Bila keduanya jatuh ke bagian yang berbeda, model di test menghadapi masukan yang hampir sama dengan yang sudah ia pelajari. Dengan 70% jendela di train, hampir setiap jendela test punya tetangga seperti itu. Yang diukur adalah kemampuan mengingat, bukan mengenali gangguan baru.

Teks paper menyebut pembagian 60/40 per periode, sedangkan kode rilis membagi acak. Kami tidak tahu mana yang sebenarnya dipakai untuk angka di paper. Hasil ini hanya menunjukkan bahwa protokol kode rilis **cukup** untuk menghasilkan angka mendekati paper, dan protokol adil tidak.

### 5.2 Alarm palsu: dua sumber hilang bersamaan

Diagnosis lama (`diagnose_alarm.py`, run 9df622b8) menemukan dua sumber alarm palsu:

1. Jendela normal di **celah antar-fault** pada run berfault. Sekitar 80% dialarm, bahkan di data train sendiri.
2. Jendela normal di **run tanpa fault** yang makin sering dialarm menjauhi blok train (drift).

Sebelum eksperimen, kami memperkirakan split acak hanya menghilangkan sumber 2, karena sumber 1 sudah gagal dipelajari di train. **Perkiraan itu salah.** FPR turun terus dari 0,218 (epoch 9) ke 0,059 (epoch 49), jauh di bawah porsi jendela celah, jadi sumber 1 ikut hilang. Penjelasan yang paling mungkin: dengan tetangga di train dan pelatihan lebih panjang (50 vs 15 epoch), model sanggup menghafal jendela celah juga. Diagnosis lama dibuat pada epoch 9.

FPR per sumber tidak diukur langsung di eksperimen ini, karena butuh menjalankan ulang model pada tiap jendela. Kesimpulan di atas adalah turunan dari angka total.

### 5.3 Cacat metrik HR@k di kode asli

Kode asli (`Eadro/codes/base.py`, fungsi `evaluate`, versi commit asli) menghitung:

```
jendela normal ditebak normal      → TP += 1
jendela gangguan terdeteksi        → TP += 1, dan hit@k bila biang ada di k teratas
jendela gangguan lolos             → FN += 1
HR@k = hit@k / (TP + FN)
```

Pembaginya, `TP + FN`, adalah **jumlah jendela gangguan ditambah jendela normal yang ditebak benar**. Akibatnya:

1. **Makin sedikit alarm palsu, makin besar pembagi, makin kecil HR@k.** Model dihukum karena makin baik membedakan normal dari gangguan.
2. **Batas atas HR@1 asli bergantung pada proporsi normal.** Bila semua normal ditebak benar dan semua biang tepat: HR@1 = 14.779 / 24.705 = **0,598**.
3. **Kriteria pilih epoch versi asli memilih epoch dengan presisi terburuk.** Di 2 dari 3 seed terpilih epoch 9, yang FPR-nya tertinggi (0,21–0,22).

Rumus ini kami uji ulang terhadap log. Dari HR@1(std), Recall(std), Precision(std), dan jumlah jendela, HR@1 asli dapat dihitung kembali: `HR@1 asli = HR@1(std) × n_gangguan / (n_gangguan + n_normal − FP)`. Hasilnya cocok dengan nilai yang dicetak kode sampai 4 desimal di **15 dari 15** titik (3 seed × 5 epoch, Lampiran A).

**Implikasi untuk angka paper.** Paper melaporkan untuk TT HR@1 0,990 sekaligus Precision 0,984. Dengan rumus asli:

- HR@1 ≥ 0,99 memaksa jendela normal yang ditebak benar ≤ sekitar 1% dari jumlah jendela gangguan.
- Precision asli ≥ 0,984 memaksa alarm palsu ≤ sekitar 1,6% dari jumlah jendela gangguan.

Jadi Test paper harus berisi **jendela normal tidak lebih dari sekitar 2,6%** dari jumlah jendela gangguan. Di data publik kita, jendela normal sekitar 40% dari Test, sebagian besar dari 3 run tanpa fault (sesuai dengan "7 jam data normal" yang disebut paper). Kemungkinannya: paper memakai rumus metrik lain, komposisi Test yang sangat berbeda, atau membuang jendela normal dari perhitungan. Kami tidak bisa memastikan yang mana. Yang bisa dikatakan: **angka HR@1 paper tidak konsisten dengan rumus di kode yang dipublikasikan bila diterapkan pada data dengan proporsi normal seperti data publik.**

Karena itu, perbandingan HR@k dengan paper sebaiknya memakai versi **(std)** (dibagi jumlah jendela gangguan saja), yang lebih dekat dengan definisi baku HR@k.

### 5.4 Sisa selisih ke paper

Di epoch 49, F1(std) 0,964 vs 0,989 (selisih 0,025) dan HR@1(std) 0,963 vs 0,990 (selisih 0,027). Penyebab yang mungkin, belum diuji:

1. **Data lebih sedikit.** Data publik hanya 81 injeksi, paper menyebut 162.
2. **Pemilihan epoch.** Tidak ada satu epoch yang terbaik di semua metrik: HR@1(std) tertinggi di sekitar epoch 29 (0,978), F1(std) di epoch 49.
3. **Pelatihan belum jenuh.** F1(std) dan Precision(std) masih naik di epoch 49; loss masih turun (0,043–0,049 di epoch 49).
4. **Pembagian acak tanpa seed di kode asli.** Pembagian yang berbeda memberi angka yang sedikit berbeda.

Selisih sekitar 0,03 tergolong wajar untuk replikasi dengan data publik yang separuh ukuran.

---

## 6. Keterbatasan

1. **Hanya satu pembagian data** (`--split-seed 0`). Variasi yang diukur (sd) hanya dari seed training, bukan dari pembagian.
2. **Epoch 49 dipilih setelah melihat hasil.** Aturan "epoch terakhir" memang aturan tetap, tetapi kami menyajikannya setelah melihat log. Dalam protokol ini seluruh pemilihan epoch memakai Test, jadi tidak ada angka yang benar-benar "tak terlihat".
3. **FPR adalah angka turunan** (Precision dan Recall dibulatkan 4 desimal di log), bukan dihitung langsung per jendela.
4. **FPR per sumber** (celah vs tanpa-fault) tidak diukur.
5. **Paper mungkin tidak memakai protokol ini.** Teks paper menyebut pembagian per periode. Kesimpulan kami terbatas pada: protokol kode rilis cukup untuk menghasilkan angka mendekati paper.

---

## 7. Yang boleh dan tidak boleh disimpulkan

| Boleh | Tidak boleh |
|---|---|
| Dengan protokol kode rilis, implementasi kita mencapai F1(std) 0,96 dan HR@1(std) 0,96–0,98, mendekati paper | "Model EADRO kita sebaik paper" tanpa menyebut protokolnya |
| Selisih besar baseline adil ke paper sebagian besar dijelaskan oleh protokol pembagian data | "Paper curang". Kita hanya tahu kode rilis bocor waktu, bukan protokol yang dipakai di paper |
| Rumus HR@k di kode rilis menghukum pengurangan alarm palsu, dan batas atasnya 0,60 di data ini | "Angka paper salah". Yang bisa dikatakan: tidak konsisten dengan rumus kode rilis pada data publik |
| Pipeline data dan perbaikan kode kita bekerja dengan benar | Angka tingkat A mengukur kemampuan generalisasi |

---

## 8. Implikasi dan langkah berikutnya

1. **Untuk laporan ke dosen**, sajikan dua angka berdampingan:
   - **Reproduksi** (tingkat A): F1(std) 0,964, HR@1(std) 0,963–0,975. Membuktikan implementasi kita benar dan angka paper bisa didekati.
   - **Evaluasi adil** (`within_event`, `leave_event_out`): F1(std) 0,77–0,81, HR@1(std) 0,65–0,82. Menunjukkan kemampuan sebenarnya pada data yang tidak bocor.
2. **Untuk perbandingan fusion**, pakai metrik (std). Jangan pakai HR@1 asli, baik sebagai metrik laporan maupun kriteria pilih epoch.
3. **Pilihan protokol untuk fusion** masih perlu diputuskan:
   - Di tingkat A semua varian kemungkinan mendekati plafon (sekitar 0,96–0,98), sehingga perbedaan antar fusion sulit terlihat.
   - Di `within_event`, sd antar seed kecil (HR@1 sd 0,03) dan masih ada ruang untuk perbaikan.
   - Usulan: `within_event` sebagai utama, tingkat A sebagai pembanding tambahan bila waktu cukup (sekitar 65–70 menit per run).
4. **Opsional**: uji pembagian acak dengan beberapa `--split-seed`, dan ukur FPR per sumber dengan `diagnose_alarm.py` pada model tingkat A.

---

## Lampiran A. Nilai Test per seed per epoch

Nilai Val identik dengan Test (salinan). "Rumus" = HR@1 asli yang dihitung ulang dari metrik (std), sebagai uji rumus di bagian 5.3.

| Seed | Epoch | F1(std) | Pre(std) | Rec(std) | HR@1(std) | HR@3(std) | F1 asli | HR@1 asli | Rumus | FPR |
|---|---|---|---|---|---|---|---|---|---|---|
| 42 | 9* | 0,924 | 0,874 | 0,981 | 0,975 | 0,981 | 0,950 | 0,6373 | 0,6374 | 0,211 |
| 42 | 19 | 0,944 | 0,916 | 0,974 | 0,972 | 0,974 | 0,964 | 0,6147 | 0,6147 | 0,134 |
| 42 | 29 | 0,948 | 0,924 | 0,974 | 0,972 | 0,974 | 0,967 | 0,6105 | 0,6105 | 0,119 |
| 42 | 39 | 0,959 | 0,960 | 0,958 | 0,957 | 0,958 | 0,975 | 0,5865 | 0,5865 | 0,060 |
| 42 | 49 | 0,963 | 0,967 | 0,958 | 0,950 | 0,958 | 0,977 | 0,5797 | 0,5797 | 0,049 |
| 7 | 9* | 0,913 | 0,866 | 0,967 | 0,961 | 0,966 | 0,942 | 0,6312 | 0,6312 | 0,223 |
| 7 | 19 | 0,915 | 0,898 | 0,934 | 0,929 | 0,934 | 0,946 | 0,5933 | 0,5933 | 0,158 |
| 7 | 29 | 0,944 | 0,908 | 0,983 | 0,979 | 0,983 | 0,964 | 0,6232 | 0,6232 | 0,149 |
| 7 | 39 | 0,959 | 0,948 | 0,971 | 0,969 | 0,971 | 0,975 | 0,5990 | 0,5990 | 0,079 |
| 7 | 49 | 0,964 | 0,964 | 0,963 | 0,962 | 0,963 | 0,978 | 0,5881 | 0,5881 | 0,053 |
| 123 | 9 | 0,924 | 0,870 | 0,986 | 0,981 | 0,985 | 0,949 | 0,6433 | 0,6433 | 0,219 |
| 123 | 19* | 0,931 | 0,878 | 0,991 | 0,989 | 0,991 | 0,954 | 0,6442 | 0,6442 | 0,204 |
| 123 | 29 | 0,944 | 0,905 | 0,986 | 0,984 | 0,986 | 0,964 | 0,6274 | 0,6273 | 0,154 |
| 123 | 39 | 0,950 | 0,947 | 0,953 | 0,952 | 0,953 | 0,969 | 0,5882 | 0,5882 | 0,080 |
| 123 | 49 | 0,965 | 0,952 | 0,978 | 0,977 | 0,978 | 0,978 | 0,6024 | 0,6024 | 0,074 |

\* Epoch terpilih oleh kriteria asli (HR@1 asli tertinggi).

## Lampiran B. Berkas terkait

| Berkas | Isi |
|---|---|
| `pipeline/build_chunks_split.py` | Skema `random_original` (opsi `--test-ratio`, `--split-seed`) |
| `work/chunks/A1/random_original/` | Data hasil pembagian, `metadata.json` (`split_seed: 0`), `split_summary.json` |
| `work/build_logs/split_random_original.log` | Log pembangunan pembagian |
| `work/result/{1c9748d6,9b5849e6,2f3b3cca}/` | `params.json`, `running.log`, `model.ckpt` tiap seed |
| `train_randomA.out` | Ringkasan grid |
| `pipeline/rekap_seed.py` | Rekap rata-rata ± sd (kini mengelompokkan menurut data dan jumlah epoch) |
| `Report/Laporan_Eksperimen_Seed.md` | Baseline protokol adil (pembanding) |
