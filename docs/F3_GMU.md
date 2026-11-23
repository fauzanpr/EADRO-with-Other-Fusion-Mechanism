# F3: Gated Multimodal Unit (GMU)

| | |
|---|---|
| Tanggal | 23 November 2026 |
| Nama di kode | `gmu` (`--fusion gmu`), kelas `GatedMultimodalUnit` di `Eadro/codes/model.py` |
| Rujukan | Arevalo, Solorio, Montes-y-Gómez, González. *Gated Multimodal Units for Information Fusion*. ICLR 2017 Workshop. `literature/Gated_Multimodal_Units_for_Information_Fusion.pdf` |
| Bagian paper yang dipakai | Bagian 3.1, Gambar 2a (versi lebih dari dua modalitas), persamaan di hal. 5 |
| Status | Kode selesai dan diuji. Eksperimen 5 seed × 2 skema selesai 23 November 2026 (hasil di bagian 13) |

## 1. Ringkasan

GMU menggabungkan tiga embedding per layanan (trace, log, metric) menjadi satu vektor. Caranya: tiap modalitas diproyeksikan sendiri, lalu dikalikan dengan **gate miliknya sendiri**. Gate itu dihitung dari ketiga modalitas sekaligus. Hasil ketiga modalitas kemudian dijumlahkan.

Bedanya dengan fusion asli EADRO (F1, `concat → Linear → GLU`) ada pada letak gate. F1 punya satu gate yang bekerja **setelah** ketiga modalitas dicampur. GMU punya satu gate **untuk tiap modalitas**, sebelum dicampur. Karena itu GMU bisa "meredam log dan memercayai metric" untuk satu layanan pada satu jendela. F1 tidak bisa membedakan modalitas sama sekali.

## 2. Rumus dari paper

Paper menuliskan versi dua modalitas (Gambar 2b) secara eksplisit:

```
h_v = tanh(W_v · x_v)
h_t = tanh(W_t · x_t)
z   = σ(W_z · [x_v, x_t])
h   = z * h_v + (1 − z) * h_t
Θ   = {W_v, W_t, W_z}
```

Untuk lebih dari dua modalitas, paper memakai Gambar 2a. Bentuknya dijelaskan dengan kata-kata (hal. 4): tiap modalitas x_i masuk ke neuron `tanh`, tiap modalitas punya neuron gate `σ`, dan gate modalitas i *"receives as input the feature vectors from all the modalities"*. Keluarannya dijumlahkan (simpul `+`). Ditulis dalam rumus untuk tiga modalitas kita:

```
h_i = tanh(W_i · x_i)                         i ∈ {trace, log, metric}
z_i = σ(W_zi · [x_trace, x_log, x_metric])
h   = z_trace ⊙ h_trace + z_log ⊙ h_log + z_metric ⊙ h_metric
```

⊙ = perkalian per elemen. Paper juga menyebut bahwa versi dua modalitas **tidak setara** dengan versi umum, karena gate-nya diikat (z dan 1 − z) agar parameternya lebih sedikit. Di kode ini dipakai versi umum (Gambar 2a), karena kita punya tiga modalitas.

## 3. Pemetaan rumus ke kode

```python
class GatedMultimodalUnit(nn.Module):
    def __init__(self, dims, out_dim, bias=False, **kwargs):
        self.proj = nn.ModuleList([nn.Linear(d, out_dim, bias=bias) for d in dims])  # W_i
        self.gate = nn.Linear(sum(dims), self.n * out_dim, bias=bias)                # [W_z1; W_z2; W_z3]

    def forward(self, trace, log, metric):
        h = stack([tanh(W_i x_i)])                       # [N, 3, out_dim]
        z = sigmoid(gate(cat(trace, log, metric)))       # [N, 3, out_dim]
        return (z * h).sum(dim=1)                        # [N, out_dim]
```

| Simbol paper | Kode | Bentuk (pengaturan default) |
|---|---|---|
| x_trace, x_log, x_metric | `trace`, `log`, `metric` (keluaran encoder tiap modalitas) | [N, 64], [N, 16], [N, 64] |
| W_i | `self.proj[i].weight` | [64, 64], [64, 16], [64, 64] |
| W_z1, W_z2, W_z3 | `self.gate.weight` (tiga matriks ditumpuk) | [3·64, 144] |
| h_i | `h[:, i, :]` | [N, 64] |
| z_i | `z[:, i, :]`, disimpan di `self.last_gates` | [N, 64] |
| h | keluaran `forward` | [N, 64] |

N = jumlah jendela dalam batch × 27 layanan. Dimensi keluaran 64 = `feat_in_dim` = `fuse_dim // 2`, sama dengan semua fusion lain. Jadi graph model (GATv2) dan kepala deteksi/lokalisasi tidak berubah sama sekali.

## 4. Keputusan implementasi

| Keputusan | Pilihan | Alasan |
|---|---|---|
| Versi GMU | Multimodal (Gambar 2a), gate tidak diikat | Kita punya tiga modalitas. Versi terikat (z, 1 − z) hanya untuk dua modalitas |
| Gate per dimensi | Ya, z_i berukuran out_dim, bukan satu skalar | Di Gambar 2a satu GMU = satu unit dengan gate skalar. Satu lapisan berisi out_dim unit, sehingga tiap dimensi keluaran punya gate sendiri |
| Masukan gate | Concat embedding mentah ketiga modalitas | Sesuai paper: `W_z · [x_v, x_t]`, bukan dari h_i |
| Aktivasi | `tanh` untuk h_i, `sigmoid` untuk z_i | Sesuai paper. Akibatnya keluaran terbatas di (−3, 3), berbeda dengan F1 yang tidak terbatas |
| Bias | **Tidak ada** (`bias=False`) | Persamaan paper tidak memuat bias dan Θ = {W_v, W_t, W_z}. Kode resmi penulis juga tanpa bias (lihat bagian 4.1). Bisa dinyalakan lewat argumen `bias=True`, tetapi belum dibuka sebagai opsi CLI |
| W_z1..W_z3 | Satu `nn.Linear` berukuran 3 × out_dim | Setara secara matematis dengan tiga `Linear` terpisah pada masukan yang sama, hanya satu perkalian matriks. Diuji di bagian 7 |
| Inisialisasi | Bawaan PyTorch | Paper mencari rentang inisialisasi lewat pencarian acak hiperparameter. Kita tidak mengulanginya agar pengaturan sama dengan F1 dan F2 |
| BatchNorm, dropout, max-norm | Tidak ditambahkan | Di paper itu bagian dari pelatihan pengklasifikasi MaxoutMLP mereka, bukan bagian dari GMU |

### 4.1 Paper vs kode resmi penulis

Kode resmi dicantumkan di catatan kaki hal. 9: `github.com/johnarevalo/gmu-mmimdb`, kelas `GatedBimodal` di `model.py` (Theano/Blocks). Isinya (dikutip, dibaca 23 November 2026):

```python
# proyeksi tiap modalitas (di GatedClassifier):  BatchNormalization -> Linear(..., use_bias=False)
x = theano.tensor.concatenate((x_1, x_2), axis=1)   # x_1, x_2 = hasil proyeksi (sebelum tanh)
h = self.activation.apply(x)                        # tanh
z = self.gate_activation.apply(x.dot(self.W))       # sigmoid, tanpa bias
return z * h[:, :self.dim] + (1 - z) * h[:, self.dim:], z
```

| Aspek | Paper (persamaan hal. 5, Gambar 2) | Kode resmi | Kode kita |
|---|---|---|---|
| Bias | Tidak ada | Tidak ada | Tidak ada |
| Gate vektor (per dimensi) | Ya | Ya | Ya |
| Jumlah modalitas | Umum (2a) dan bimodal (2b) | Hanya bimodal, gate diikat (z, 1 − z) | Umum (2a), 3 gate |
| **Masukan gate** | **x mentah**: σ(W_z·[x_v, x_t]) | **hasil proyeksi** sebelum tanh: σ(W·[W_v x_v, W_t x_t]) | **x mentah**, ikut paper |
| BatchNorm sebelum proyeksi | Tidak disebut di persamaan | Ada, pada fitur masukan tiap modalitas | Tidak ada |

Perbedaan masukan gate tidak dijelaskan di paper. Kode ini mengikuti **persamaan paper**, karena paper itulah rujukan yang dikutip di laporan. Gate dari x mentah juga lebih dekat dengan uraian paper (hal. 4: gate *"receives as input the feature vectors from all the modalities"*). Konsekuensinya, gate kita punya parameter sendiri berukuran 144 × 192, sedangkan di kode resmi gate membaca vektor yang sudah diproyeksikan (2·dim × dim).

BatchNorm di kode resmi bekerja pada fitur yang sudah jadi (VGG, word2vec), jadi itu bagian dari penyiapan masukan, bukan bagian dari unit GMU. Di model kita, masukan GMU adalah keluaran encoder yang ikut dilatih, sama seperti masukan F1 dan F2. Menambah BatchNorm hanya di F3 akan membuat perbandingan tidak setara.

Jika nanti ingin menguji varian kode resmi (gate dari hasil proyeksi), cukup ubah satu baris di `forward`. Varian itu sebaiknya diberi nama sendiri, bukan menggantikan `gmu`.

## 5. Posisi di dalam model

```
trace  [N, T, 1]  → TraceModel  (Conv1d + self-attn) → x_trace  [N, 64] ┐
log    [N, E]     → LogModel    (Linear)              → x_log    [N, 16] ├→ GMU → h [N, 64] → GATv2 (graf 27 layanan) → deteksi + lokalisasi
metric [N, T, M]  → MetricModel (Conv1d + self-attn)  → x_metric [N, 64] ┘
```

Hanya kotak fusion yang diganti. Encoder, graf, kepala, loss, dan pengaturan latih tetap sama dengan F1 dan F2.

## 6. Perbandingan dengan fusion lain

| | Rumus | Gate |
|---|---|---|
| F1 `concat_glu` (EADRO) | (A·[x]) ⊙ σ(B·[x]) = (Σᵢ Aᵢxᵢ) ⊙ σ(B·[x]) | Satu gate untuk campuran ketiga modalitas |
| F2 `concat_fc` | ReLU(Σᵢ Aᵢxᵢ) | Tidak ada |
| **F3 `gmu`** | Σᵢ tanh(Wᵢxᵢ) ⊙ σ(W_zᵢ·[x]) | Satu gate per modalitas, per dimensi, dari ketiga modalitas |
| `attn` (bukan F3) | Σᵢ wᵢ · ReLU(Pᵢxᵢ), w = softmax | Satu skalar per modalitas, jumlahnya dipaksa 1 |

[x] = concat ketiga embedding. Bagian linear F1 pada concat sama dengan Σᵢ Aᵢxᵢ, jadi F1 sudah ber-gate, tetapi gate-nya tidak tahu modalitas mana yang menyumbang. Jika ketiga gate GMU dipaksa sama, bentuknya kembali mirip F1 (dengan tanh per modalitas). Rangkaian F1 → F2 → F3 karena itu menjawab dua pertanyaan:

1. F1 vs F2: apakah gate perlu? (Hasil 5 seed: tidak bisa dibedakan secara meyakinkan.)
2. F1 vs F3: jika memakai gate, apakah lebih baik per modalitas daripada setelah dicampur?

Alasan GMU layak diuji di data microservice: jenis gangguan yang berbeda memunculkan gejala di modalitas yang berbeda (resource di metric, jaringan di latensi trace, error di log), dan dalam satu jendela ada layanan yang log atau trace-nya hampir kosong. Gate yang bergantung pada input bisa meredam modalitas yang kosong atau berisi noise. Di paper (bagian 5.1, data sintetis), gate z berkorelasi 1 dengan variabel tersembunyi yang menentukan modalitas mana yang informatif. Itu argumen mekanisme, bukan bukti bahwa GMU akan unggul di data TT. Di MM-IMDb (Tabel 2), keunggulan GMU atas concat kecil (F-weighted 0,617 vs 0,597), dari satu dataset dan tanpa sebaran seed.

## 7. Verifikasi yang sudah dilakukan

Uji dijalankan dengan env `work/envs/train312`. Hasil uji cepat disimpan di scratchpad, bukan di `work/result`.

| Uji | Hasil |
|---|---|
| Bentuk keluaran dan gate | h [270, 64], z [270, 3, 64] |
| Cocok dengan rumus paper (dihitung ulang manual dengan tiga W_zi terpisah) | Selisih maksimum 1,8 × 10⁻⁷ (presisi float32) |
| Semua parameter mendapat gradien | Ya |
| Tanpa bias | Ya, parameter hanya bobot |
| Gate saat inisialisasi | Rata-rata 0,50, rentang 0,07–0,94 |
| Latih 1 epoch, `within_event`, seed 42, data asli T = 10 | Berjalan tanpa galat, loss 1,558, Val combo 0,681. `params_total` 84.354, `params_fusion` 36.864 |

Angka 1 epoch hanya bukti bahwa kode berjalan, bukan hasil.

## 8. Efisiensi

Diukur dengan `pipeline/ukur_efisiensi.py --mode fusion` (T = 10, data acak, median 3 ronde, torch 4 thread). Derau waktu antar ronde sekitar ±10–20%.

| Fusion | Params total | Params fusion | FLOPs / jendela | Latensi 1 jendela (ms) | ms / jendela, batch 256 | Latih ms / jendela |
|---|---|---|---|---|---|---|
| F1 `concat_glu` | 66.050 | 18.560 | 3,59 M | 2,87 | 0,306 | 2,00 |
| F2 `concat_fc` | 56.770 | 9.280 | 3,09 M | 2,84 | 0,301 | 2,00 |
| **F3 `gmu`** | **84.354** | **36.864** | **4,58 M** | **3,02** | **0,328** | **2,06** |

- Parameter fusion GMU = 2 × F1. Total parameter model naik **+28%** (66.050 → 84.354), FLOPs juga +28%. Fusion bukan bagian kecil dari model ini, karena model EADRO di T = 10 hanya ±66 ribu parameter.
- Waktu naik 3–7%, masih di dalam derau pengukuran. Tidak bisa disebut lebih lambat secara terukur.
- Dari mana 36.864: proyeksi (64 + 16 + 64) × 64 = 9.216, gate 144 × 192 = 27.648.

## 9. Cara menjalankan

Pengaturan sama dengan F1 dan F2 lima seed: T = 10 (`A1`), 15 epoch, pemilihan epoch lewat Val `combo`, seed 42, 7, 123, 31, 2026.

```bash
nohup pipeline/run_grid.sh within_event    15 "42 7 123 31 2026" "gmu" > grid_gmu_we.out  2>&1 &
# setelah yang pertama selesai (jangan paralel, agar waktu per epoch tetap sebanding):
nohup pipeline/run_grid.sh leave_event_out 15 "42 7 123 31 2026" "gmu" > grid_gmu_leo.out 2>&1 &
```

Atau berurutan dalam satu perintah:

```bash
nohup sh -c 'pipeline/run_grid.sh within_event 15 "42 7 123 31 2026" "gmu"; pipeline/run_grid.sh leave_event_out 15 "42 7 123 31 2026" "gmu"' > grid_gmu.out 2>&1 &
```

Perkiraan: 10 run × ±16 menit ≈ 2,5–3 jam. Run yang sudah selesai dicatat di `work/result/grid_selesai.txt` dan dilewati bila skrip dijalankan ulang.

Rekap setelah selesai:

```bash
work/envs/train312/bin/python -I pipeline/rekap_semua.py --gambar   # GMU muncul sebagai "T=10 F3"
work/envs/train312/bin/python -I pipeline/baca_hasil.py
```

## 10. Membaca nilai gate

Setiap forward pass menyimpan gate terakhir di `model.encoder.fusion_module.last_gates`, berukuran [N, 3, 64] dengan urutan modalitas (trace, log, metric). Rata-rata atas dimensi terakhir memberi satu angka per layanan per modalitas. Ini belum dicatat otomatis saat latih maupun evaluasi. Jika nanti dipakai untuk analisis (misalnya per event atau per jenis gangguan), perlu skrip terpisah yang memuat `model.ckpt` lalu menjalankan Test.

Hati-hati menafsirkan: z_i besar tidak otomatis berarti modalitas i penting, karena besar h_i = tanh(W_i x_i) juga berbeda antar modalitas. Yang lebih jujur adalah melihat kontribusi z_i ⊙ h_i, atau melakukan ablasi modalitas sungguhan.

## 11. Keterbatasan dan hal yang perlu diwaspadai

1. **Kapasitas tidak sama.** GMU punya 2× parameter fusion F1 dan +28% parameter total. Jika F3 lebih baik, sebagian bisa karena kapasitas, bukan karena gate per modalitas. Dimensi keluaran tidak diubah agar kontrak antar-fusion tetap sama.
2. **Tidak ada bias**, sesuai persamaan paper. Fusion lain di kode memakai bias. Ini sengaja, demi kesetiaan pada paper.
3. **Keluaran terbatas (−3, 3)** karena tanh, sedangkan F1 tidak terbatas. GATv2 sesudahnya menerima skala masukan yang berbeda. Ini bagian dari desain GMU, bukan galat.
4. **Hiperparameter tidak disetel ulang** untuk GMU (lr 0,001, batch 256, 15 epoch, sama dengan F1 dan F2). Perbandingan adil dalam pengaturan yang sama, tetapi belum tentu pengaturan terbaik untuk GMU.
5. **Bukti dari paper lemah:** satu dataset, satu run, selisih kecil. Jangan ditulis "GMU terbukti lebih baik". Klaim hanya dibuat bila CI selisih 5 seed tidak memuat 0, seperti pada F1 vs F2.

## 12. File yang diubah

| File | Perubahan |
|---|---|
| `Eadro/codes/model.py` | Kelas `GatedMultimodalUnit`; `"gmu"` ditambahkan ke `FUSIONS` dan `FUSION_MODULES` |
| `pipeline/baca_hasil.py` | `"gmu"` di `FUSION_ORDER` (urutan dan warna gambar: F1, F2, F3, lalu varian lain) |
| `pipeline/rekap_semua.py` | Label `gmu` → "F3" |

`main.py` tidak perlu diubah: pilihan `--fusion` diambil dari `FUSIONS`, dan `params_fusion` sudah menghitung parameter berawalan `fusion_module.`.

## 13. Hasil 5 seed (T = 10, 15 epoch)

Dijalankan 23 November 2026, 14.33–17.17 (2 jam 44 menit, 10 run, tanpa galat). Rekap: `work/envs/train312/bin/python -I pipeline/banding_fusion.py`. Metrik Test (std) pada epoch yang dipilih Val. Selisih = F3 − pembanding, CI 95% Welch, **tebal** = CI tidak memuat 0, p = uji permutasi. FPR dan HR@1 bersyarat adalah turunan (rumus di skrip). Test: `within_event` 17.990 jendela gangguan + 14.200 normal, `leave_event_out` 16.452 + 10.900.

### 13.1 `within_event`

| Ukuran | F1 | F2 | F3 GMU | F3 − F1 (CI) | p | F3 − F2 (CI) | p |
|---|---|---|---|---|---|---|---|
| F1(std) | 0,763 ± 0,014 | 0,805 ± 0,031 | 0,808 ± 0,064 | +0,045 (−0,033 s.d. +0,123) | 0,175 | +0,002 (−0,076 s.d. +0,081) | 0,960 |
| Precision | 0,655 ± 0,036 | 0,709 ± 0,047 | 0,704 ± 0,091 | +0,049 (−0,063 s.d. +0,160) | 0,302 | −0,006 | 0,897 |
| Recall | 0,916 ± 0,032 | 0,935 ± 0,035 | 0,955 ± 0,019 | +0,040 (−0,001 s.d. +0,080) | 0,056 | +0,021 | 0,262 |
| HR@1(std) | 0,814 ± 0,024 | 0,844 ± 0,031 | 0,856 ± 0,022 | **+0,042 (+0,008 s.d. +0,075)** | 0,024 | +0,011 (−0,029 s.d. +0,052) | 0,532 |
| HR@3(std) | 0,874 ± 0,021 | 0,896 ± 0,031 | 0,911 ± 0,023 | **+0,037 (+0,004 s.d. +0,069)** | 0,040 | +0,015 | 0,413 |
| NDCG@3(std) | 0,850 ± 0,022 | 0,875 ± 0,031 | 0,889 ± 0,022 | **+0,039 (+0,007 s.d. +0,071)** | 0,032 | +0,013 | 0,476 |
| FPR | 0,618 ± 0,112 | 0,492 ± 0,113 | 0,534 ± 0,238 | −0,084 (−0,376 s.d. +0,208) | 0,452 | +0,042 | 0,706 |
| HR@1 bersyarat | 0,890 ± 0,032 | 0,904 ± 0,022 | 0,896 ± 0,019 | +0,006 | 0,714 | −0,008 | 0,556 |

Per seed F3 (42, 7, 123, 31, 2026): F1(std) 0,864 / 0,869 / 0,729 / 0,754 / 0,822; HR@1(std) 0,834 / 0,887 / 0,860 / 0,835 / 0,862; FPR 0,33 / 0,34 / 0,87 / 0,69 / 0,44. Epoch terpilih: 9 di 4 dari 5 run.

### 13.2 `leave_event_out`

| Ukuran | F1 | F2 | F3 GMU | F3 − F1 (CI) | p | F3 − F2 (CI) | p |
|---|---|---|---|---|---|---|---|
| F1(std) | 0,800 ± 0,047 | 0,824 ± 0,049 | 0,858 ± 0,014 | **+0,059 (+0,001 s.d. +0,116)** | 0,016 | +0,035 (−0,026 s.d. +0,095) | 0,198 |
| Precision | 0,720 ± 0,054 | 0,763 ± 0,050 | 0,793 ± 0,027 | **+0,073 (+0,006 s.d. +0,139)** | 0,048 | +0,030 | 0,238 |
| Recall | 0,903 ± 0,071 | 0,898 ± 0,072 | 0,937 ± 0,019 | +0,034 (−0,053 s.d. +0,120) | 0,349 | +0,038 | 0,286 |
| HR@1(std) | 0,582 ± 0,118 | 0,533 ± 0,073 | 0,605 ± 0,029 | +0,023 (−0,121 s.d. +0,167) | 0,746 | +0,072 (−0,018 s.d. +0,161) | 0,056 |
| HR@3(std) | 0,699 ± 0,103 | 0,638 ± 0,088 | 0,738 ± 0,019 | +0,039 (−0,088 s.d. +0,167) | 0,405 | +0,100 (−0,008 s.d. +0,208) | 0,024 |
| NDCG@3(std) | 0,650 ± 0,110 | 0,595 ± 0,082 | 0,683 ± 0,025 | +0,033 | 0,532 | +0,089 (−0,011 s.d. +0,189) | 0,024 |
| FPR | 0,535 ± 0,132 | 0,425 ± 0,121 | 0,371 ± 0,067 | **−0,164 (−0,326 s.d. −0,002)** | 0,063 | −0,054 | 0,484 |
| HR@1 bersyarat | 0,641 ± 0,090 | 0,591 ± 0,043 | 0,645 ± 0,028 | +0,004 | 0,929 | +0,054 (−0,001 s.d. +0,109) | 0,071 |

Per seed F3: F1(std) 0,851 / 0,859 / 0,841 / 0,867 / 0,875; HR@1(std) 0,588 / 0,638 / 0,619 / 0,564 / 0,613; FPR 0,37 / 0,35 / 0,49 / 0,31 / 0,35.

### 13.3 Pembacaan

1. **F3 hampir tidak pernah di bawah F1 atau F2 secara rata-rata.** Terhadap F1, semua 16 selisih (8 ukuran × 2 skema) searah menguntungkan F3. Terhadap F2, hanya tiga yang berlawanan arah, semuanya di `within_event` dan jauh dari terbukti: Precision −0,006, HR@1 bersyarat −0,008, FPR +0,042.
2. **`within_event`: F3 melokalisasi lebih baik dari F1** (HR@1 +0,042, HR@3, NDCG@3 searah, CI tidak memuat 0). Ketiganya ukuran yang saling berkaitan, jadi ini satu temuan, bukan tiga. Sumbernya Recall (+0,040), bukan ketepatan lokalisasi: HR@1 bersyarat sama (0,896 vs 0,890). Artinya F3 mendeteksi lebih banyak gangguan, dan gangguan yang terdeteksi dilokalisasi sama baiknya. Terhadap F2 tidak ada selisih.
3. **`leave_event_out`: F3 mendeteksi lebih baik dari F1** (F1(std) +0,059, Precision +0,073, FPR −0,164), tetapi tipis: batas CI +0,001 dan −0,002, dan p permutasi FPR 0,063 tidak sepakat dengan CI. Terhadap F2: lokalisasi F3 lebih tinggi (HR@3 +0,100, p permutasi 0,024), tetapi CI Welch memuat 0.
4. **Sebaran antar seed F3 di `leave_event_out` jauh lebih kecil** (sd HR@1 0,029 vs 0,118 F1; F1(std) 0,014 vs 0,047). Uji Levene belum terbukti (p 0,09 dan 0,10). Di `within_event` justru sebaliknya: F1(std) F3 lebih tersebar (sd 0,064 vs 0,014, Levene p 0,03), karena seed 123 dan 31 punya FPR tinggi (0,87 dan 0,69). Jadi "GMU lebih stabil" belum bisa diklaim.
5. **Banyak perbandingan.** 8 ukuran × 2 skema × 2 pembanding = 32 selisih, 6 CI tidak memuat 0, berupa dua kelompok yang saling berkaitan (lokalisasi `within_event`, deteksi `leave_event_out`). Bila semua selisih nol, kira-kira 1–2 akan lolos karena kebetulan. Dua dari enam nyaris di batas.
6. **Kapasitas.** F3 punya +28% parameter total dibanding F1 (bagian 8, 11.1). Keunggulan atas F1 belum bisa dipisahkan dari efek kapasitas. Terhadap F2 (parameter jauh lebih sedikit), F3 tidak terbukti lebih baik.

### 13.4 Kalimat yang aman

> Dengan 5 seed, GMU (F3) setara atau sedikit lebih baik dari fusion asli EADRO (F1): semua selisih rata-ratanya searah menguntungkan F3. Keunggulan yang CI-nya tidak memuat 0 hanya dua dan tipis: lokalisasi di `within_event` (HR@1 +0,04, berasal dari Recall yang lebih tinggi) dan deteksi di `leave_event_out` (F1(std) +0,06, Precision lebih tinggi, alarm palsu lebih sedikit). Terhadap F2 tidak ada selisih yang terbukti. Karena F3 memakai 28% parameter lebih banyak dari F1, keunggulan ini belum bisa dikaitkan khusus pada gate per modalitas.

Waktu latih: 53 s/epoch (`within_event`) dan 60 s/epoch (`leave_event_out`), F1 51 dan 58. Sama dalam batas derau.
