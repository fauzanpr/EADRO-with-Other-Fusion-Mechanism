# Perbandingan Seluruh Eksperimen, per Seed

| | |
|---|---|
| Tanggal | 23 November 2026 (pembaruan 24 November: cek epoch T = 30, bagian 5.8, dan fusion T = 30 `within_event`, bagian 5.9; pembaruan 25 November: fusion T = 30 `leave_event_out`, bagian 5.10; pembaruan 26 November: F1w, kontrol kapasitas, bagian 5.11; pembaruan 27 November: T = 10 `leave_event_out` dengan 30 epoch, bagian 5.12) |
| Data | Train Ticket (TT), `A1`, jendela T = 5, 10, 30, 40, 50, 60 detik |
| Eksperimen | 29 kelompok, 123 run: sweep T (F1), perbandingan fusion F1, F2, F3 (GMU) di T = 10 dan T = 30 (kedua skema), F1w (kontrol kapasitas), cek epoch T = 30, kontrol epoch T = 10 (30 epoch), dan `random_original` |
| Alur eksperimen | `Report/Jurnal_Eksperimen.md` (kenapa tiap eksperimen dibuat, urut waktu) |
| Pengaturan | 15 epoch, batch 256, lr 0,001, epoch dipilih lewat Val (`combo`), evaluasi tiap 5 epoch. Fusion T = 30 `leave_event_out`: 30 epoch. Kontrol epoch T = 10 `leave_event_out`: 30 epoch. `random_original`: 50 epoch, dipilih lewat HR@1 |
| Seed | 42, 7, 123 (semua), 31 dan 2026 (T = 10 F1/F2/F3, T = 30 `within_event` F1/F2/F3, T = 30 `leave_event_out` 30 epoch F1/F2/F3, F1w di T = 10 dan T = 30 `leave_event_out`, T = 10 `leave_event_out` 30 epoch F1/F1w/F2/F3) |
| Metrik | Test, versi (std). Nilai pada epoch yang terpilih lewat Val |
| Rekap | `work/envs/train312/bin/python -I pipeline/rekap_semua.py --gambar` |
| Gambar | `Report/Gambar_Seed_Semua.png` |

Laporan ini menyatukan hasil dari `Temuan_Data_dan_Sweep_T.md`, `Laporan_Fusion_F1_vs_F2.md` (termasuk F3, bagian 10), `Laporan_Eksperimen_Seed.md`, dan `docs/F3_GMU.md`, dengan **nilai tiap seed ditampilkan** supaya terlihat seberapa besar sebaran yang disebabkan seed saja. Run uji awal (n = 1, 30 dan 50 epoch di T = 10) tidak diikutkan.

## Ringkasan

1. **Sebaran antar seed sering sama besar dengan selisih antar eksperimen.** Contoh `leave_event_out`, HR@1(std) T = 10 F1: lima seed berkisar 0,461 sampai 0,759. Selisih antar T atau antar fusion di skema ini umumnya lebih kecil dari rentang itu.
2. **Kualitas deteksi (F1(std)) naik bersama T**, dan kenaikan itu cukup jelas di beberapa titik: `within_event` T = 30 (+0,067, n = 5) dan `leave_event_out` T = 50 (+0,105) serta T = 60 (+0,096), terhadap T = 10. Kenaikan itu datang dari Recall yang mendekati 1 (0,97–0,99) dan Precision yang ikut naik.
3. **Lokalisasi (HR@1(std)) tidak membaik dengan T besar.** Tidak ada satu pun selisih HR@1 terhadap T = 10 yang CI-nya lepas dari 0, di kedua skema.
4. **Fusion di T = 10 (F1, F2, F3):** F3 (GMU) setara atau sedikit lebih baik dari F1. Semua selisih rata-ratanya menguntungkan F3, tetapi hanya dua yang CI-nya tidak memuat 0, dan keduanya tipis: HR@1(std) `within_event` +0,042 (CI +0,008 s.d. +0,075) dan F1(std) `leave_event_out` +0,059 (CI +0,001 s.d. +0,116). F2 terhadap F1: hanya F1(std) `within_event` +0,043 (CI +0,005 s.d. +0,081). F3 terhadap F2: tidak ada selisih terbukti. F3 memakai 28% parameter lebih banyak dari F1.
5. **Hati-hati menafsirkan "terbukti".** Ada 26 selisih terhadap T = 10 F1 yang diuji tanpa koreksi, 7 di antaranya CI-nya tidak memuat 0. Tiga di antaranya tipis (batas bawah +0,001, +0,004, dan +0,005). Test set juga berbeda antar T. Baca sebagai petunjuk yang menguatkan arah, bukan bukti tiap angka.
6. **Fusion di T = 30 `within_event` (n = 5):** F1, F2, F3 setara. F2 − F1 F1(std) tinggal +0,009, F3 − F1 HR@1(std) +0,004. Satu-satunya selisih yang lolos adalah HR@1 bersyarat F3 (+0,023 terhadap F1, CI +0,003 s.d. +0,043), tipis. Di `within_event`, tidak ada selisih fusion yang lolos di T = 10 dan T = 30 sekaligus. Di T = 30, selisih antar fusion (paling besar +0,035) lebih kecil dari selisih antar T (+0,07 s.d. +0,10 terhadap T = 10 F1). Lihat bagian 5.9.
7. **Fusion di T = 30 `leave_event_out` (n = 5, 30 epoch): F3 lebih baik dari F1 dan F2 untuk deteksi.** F1(std) 0,910 vs 0,849 / 0,850 (+0,061, CI +0,013 s.d. +0,109 terhadap F1; +0,060, CI +0,010 s.d. +0,110 terhadap F2). Sumbernya alarm palsu: FPR 0,240 vs 0,439 / 0,492, lebih rendah di kelima seed. HR@1(std) tidak berbeda (0,599 vs 0,560 / 0,591). F2 setara F1. Terhadap F1, kenaikan F1(std) dan turunnya FPR oleh F3 juga lolos di T = 10 `leave_event_out` dengan besar yang hampir sama. **Ini selisih fusion pertama yang berulang di dua T.** Lihat bagian 5.10.
8. **Jumlah seed tidak seimbang:** T = 10 dan T = 30 (fusion) punya 5 seed, T lain hanya 3. Karena itu CI di T lain lebar, dan selisih besar (misalnya T = 60 `within_event` +0,130) tetap belum terbukti.
9. **Kontrol kapasitas F1w (26 November, n = 5):** F1 yang diperbesar sampai parameter fusion setara F3 (36.983 vs 36.864). **Di T = 30 `leave_event_out`, F1w = F1** (F1(std) 0,850, FPR 0,438), dan F3 tetap unggul atas F1w (F1(std) +0,060, CI +0,010 s.d. +0,110; FPR −0,199). Keunggulan F3 di setting itu berasal dari arsitektur, bukan kapasitas. **Di T = 10, F1w menyamai F3** dalam deteksi, dan di `leave_event_out` HR@1 F1w lebih tinggi (0,667 vs 0,605, CI −0,118 s.d. −0,006 untuk F3 − F1w). Lihat bagian 5.11.
10. **Kontrol epoch (27 November, n = 5): T = 10 `leave_event_out` diulang dengan 30 epoch.** Tidak ada fusion yang berubah (F1(std) 30 − 15 epoch antara −0,014 dan +0,007, semua p ≥ 0,26), jadi 15 epoch cukup di T = 10. Pada epoch yang sama, F3 ≈ F1w di T = 10 (F1(std) 0,844 vs 0,853) tetapi F3 > F1w di T = 30 (0,910 vs 0,850). **Keunggulan GMU atas F1w bergantung pada T, bukan pada lama training** (dua titik T). Lihat bagian 5.12.

---

## 1. Daftar eksperimen dan seed

| Kelompok | Skema | Seed | Jumlah run |
|---|---|---|---|
| T = 5, F1 | `within_event` | 42, 7, 123 | 3 |
| T = 10, F1 (`concat_glu`) | `within_event`, `leave_event_out` | 42, 7, 123, 31, 2026 | 10 |
| T = 10, F2 (`concat_fc`) | `within_event`, `leave_event_out` | 42, 7, 123, 31, 2026 | 10 |
| T = 10, F3 (`gmu`, GMU) | `within_event`, `leave_event_out` | 42, 7, 123, 31, 2026 | 10 |
| T = 30, F1 | `within_event` | 42, 7, 123, 31, 2026 | 5 |
| T = 30, F1 | `leave_event_out` | 42, 7, 123 | 3 |
| T = 30, F2 (`concat_fc`) | `within_event` | 42, 7, 123, 31, 2026 | 5 |
| T = 30, F3 (`gmu`) | `within_event` | 42, 7, 123, 31, 2026 | 5 |
| T = 40, 50, 60, F1 | `within_event`, `leave_event_out` | 42, 7, 123 | 18 |
| T = 10, F1, 50 epoch | `random_original` | 42, 7, 123 | 3 |
| T = 30, F1, 30 epoch (cek epoch) | `within_event` | 42 | 1 |
| T = 30, F1, F2, F3, 30 epoch | `leave_event_out` | 42, 7, 123, 31, 2026 | 15 |
| T = 10, F1w (`concat_glu_wide`) | `within_event`, `leave_event_out` | 42, 7, 123, 31, 2026 | 10 |
| T = 30, F1w, 30 epoch | `leave_event_out` | 42, 7, 123, 31, 2026 | 5 |
| T = 10, F1, F1w, F2, F3, 30 epoch (kontrol epoch) | `leave_event_out` | 42, 7, 123, 31, 2026 | 20 |
| **Total** | | | **103** |

Run cek epoch `leave_event_out` (F1 seed 42, 30 epoch, `14f5c50b`) dipakai ulang sebagai F1 seed 42 dalam kelompok fusion T = 30 `leave_event_out` 30 epoch, sehingga hanya 14 run yang baru.

T = 5 hanya dijalankan di `within_event`. F3 = Gated Multimodal Unit (Arevalo dkk., 2017), lihat `docs/F3_GMU.md`. F4 belum ada.

## 2. Cara membaca

- Seed mengubah inisialisasi bobot dan urutan batch. Pembagian data tidak berubah (dibagi per event), dan Test tetap sama untuk semua seed pada satu T.
- Angka dalam kurung = epoch yang terpilih lewat Val untuk run itu. Epoch 4 berarti run yang Val-nya paling baik di awal.
- "Selisih" = rata-rata eksperimen − rata-rata baseline T = 10 F1 (skema yang sama). CI 95% memakai Welch. Selisih dianggap terbukti hanya bila CI tidak memuat 0 (dicetak **tebal**).
- Test berisi jumlah jendela yang berbeda untuk tiap T, sehingga selisih antar T tidak murni efek T saja.

## 3. Hasil

### 3.1 `within_event`

**F1(std) per seed** (epoch terpilih dalam kurung)

| Eksperimen | n | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 | rata-rata ± sd | min – maks |
|---|---|---|---|---|---|---|---|---|
| T=5 F1 | 3 | 0,708 (9) | 0,742 (4) | 0,779 (9) | – | – | 0,743 ± 0,036 | 0,708 – 0,779 |
| T=10 F1 | 5 | 0,786 (14) | 0,758 (14) | 0,757 (9) | 0,763 (14) | 0,749 (9) | 0,763 ± 0,014 | 0,749 – 0,786 |
| T=10 F2 | 5 | 0,782 (14) | 0,836 (9) | 0,837 (9) | 0,768 (14) | 0,803 (9) | 0,805 ± 0,031 | 0,768 – 0,837 |
| T=10 F3 | 5 | 0,864 (9) | 0,869 (9) | 0,729 (9) | 0,754 (9) | 0,822 (14) | 0,808 ± 0,064 | 0,729 – 0,869 |
| T=30 F1 | 5 | 0,847 (9) | 0,851 (4) | 0,834 (9) | 0,811 (9) | 0,803 (4) | 0,829 ± 0,021 | 0,803 – 0,851 |
| T=30 F2 | 5 | 0,853 (4) | 0,810 (9) | 0,821 (9) | 0,856 (9) | 0,853 (9) | 0,839 ± 0,022 | 0,810 – 0,856 |
| T=30 F3 | 5 | 0,887 (14) | 0,909 (9) | 0,889 (4) | 0,854 (4) | 0,784 (9) | 0,865 ± 0,049 | 0,784 – 0,909 |
| T=40 F1 | 3 | 0,772 (9) | 0,864 (9) | 0,833 (9) | – | – | 0,823 ± 0,047 | 0,772 – 0,864 |
| T=50 F1 | 3 | 0,817 (14) | 0,851 (14) | 0,894 (14) | – | – | 0,854 ± 0,039 | 0,817 – 0,894 |
| T=60 F1 | 3 | 0,930 (14) | 0,824 (14) | 0,922 (14) | – | – | 0,892 ± 0,059 | 0,824 – 0,930 |

**HR@1(std) per seed** (epoch terpilih dalam kurung)

| Eksperimen | n | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 | rata-rata ± sd | min – maks |
|---|---|---|---|---|---|---|---|---|
| T=5 F1 | 3 | 0,809 (9) | 0,801 (4) | 0,787 (9) | – | – | 0,799 ± 0,011 | 0,787 – 0,809 |
| T=10 F1 | 5 | 0,809 (14) | 0,857 (14) | 0,799 (9) | 0,805 (14) | 0,801 (9) | 0,814 ± 0,024 | 0,799 – 0,857 |
| T=10 F2 | 5 | 0,797 (14) | 0,848 (9) | 0,882 (9) | 0,837 (14) | 0,859 (9) | 0,844 ± 0,031 | 0,797 – 0,882 |
| T=10 F3 | 5 | 0,834 (9) | 0,887 (9) | 0,860 (9) | 0,835 (9) | 0,862 (14) | 0,856 ± 0,022 | 0,834 – 0,887 |
| T=30 F1 | 5 | 0,837 (9) | 0,821 (4) | 0,839 (9) | 0,824 (9) | 0,845 (4) | 0,833 ± 0,010 | 0,821 – 0,845 |
| T=30 F2 | 5 | 0,840 (4) | 0,828 (9) | 0,801 (9) | 0,840 (9) | 0,828 (9) | 0,828 ± 0,016 | 0,801 – 0,840 |
| T=30 F3 | 5 | 0,782 (14) | 0,850 (9) | 0,855 (4) | 0,870 (4) | 0,825 (9) | 0,837 ± 0,034 | 0,782 – 0,870 |
| T=40 F1 | 3 | 0,728 (9) | 0,869 (9) | 0,876 (9) | – | – | 0,824 ± 0,084 | 0,728 – 0,876 |
| T=50 F1 | 3 | 0,892 (14) | 0,811 (14) | 0,847 (14) | – | – | 0,850 ± 0,041 | 0,811 – 0,892 |
| T=60 F1 | 3 | 0,847 (14) | 0,830 (14) | 0,851 (14) | – | – | 0,842 ± 0,011 | 0,830 – 0,851 |

**Rata-rata ± sd, semua ukuran (Test, std)**

| Eksperimen | n | F1 | Pre | Rec | HR@1 | HR@3 | s/epoch |
|---|---|---|---|---|---|---|---|
| T=5 F1 | 3 | 0,743 ± 0,036 | 0,616 ± 0,062 | 0,942 ± 0,038 | 0,799 ± 0,011 | 0,878 ± 0,031 | 32 |
| T=10 F1 | 5 | 0,763 ± 0,014 | 0,655 ± 0,036 | 0,916 ± 0,032 | 0,814 ± 0,024 | 0,874 ± 0,021 | 51 |
| T=10 F2 | 5 | 0,805 ± 0,031 | 0,709 ± 0,047 | 0,935 ± 0,035 | 0,844 ± 0,031 | 0,896 ± 0,031 | 56 |
| T=10 F3 | 5 | 0,808 ± 0,064 | 0,704 ± 0,091 | 0,955 ± 0,019 | 0,856 ± 0,022 | 0,911 ± 0,023 | 53 |
| T=30 F1 | 5 | 0,829 ± 0,021 | 0,725 ± 0,034 | 0,970 ± 0,009 | 0,833 ± 0,010 | 0,913 ± 0,010 | 125 |
| T=30 F2 | 5 | 0,839 ± 0,022 | 0,742 ± 0,031 | 0,966 ± 0,020 | 0,828 ± 0,016 | 0,906 ± 0,025 | 125 |
| T=30 F3 | 5 | 0,865 ± 0,049 | 0,798 ± 0,084 | 0,949 ± 0,026 | 0,837 ± 0,034 | 0,908 ± 0,034 | 127 |
| T=40 F1 | 3 | 0,823 ± 0,047 | 0,732 ± 0,057 | 0,940 ± 0,039 | 0,824 ± 0,084 | 0,894 ± 0,057 | 168 |
| T=50 F1 | 3 | 0,854 ± 0,039 | 0,765 ± 0,067 | 0,970 ± 0,007 | 0,850 ± 0,041 | 0,922 ± 0,042 | 214 |
| T=60 F1 | 3 | 0,892 ± 0,059 | 0,814 ± 0,095 | 0,992 ± 0,001 | 0,842 ± 0,011 | 0,933 ± 0,011 | 260 |

**Selisih terhadap baseline T=10 F1** (rata-rata eksperimen − rata-rata baseline, CI 95% Welch; **tebal** = CI tidak memuat 0)

| Eksperimen | n | ΔF1(std) | CI 95% | ΔHR@1(std) | CI 95% |
|---|---|---|---|---|---|
| T=5 F1 | 3 | −0,020 | −0,099 s.d. +0,060 | −0,015 | −0,046 s.d. +0,016 |
| T=10 F2 | 5 | **+0,043** | +0,005 s.d. +0,081 | +0,030 | −0,011 s.d. +0,071 |
| T=10 F3 | 5 | +0,045 | −0,033 s.d. +0,123 | **+0,042** | +0,008 s.d. +0,075 |
| T=30 F1 | 5 | **+0,067** | +0,040 s.d. +0,094 | +0,019 | −0,011 s.d. +0,048 |
| T=30 F2 | 5 | **+0,076** | +0,049 s.d. +0,104 | +0,013 | −0,017 s.d. +0,044 |
| T=30 F3 | 5 | **+0,102** | +0,042 s.d. +0,162 | +0,022 | −0,022 s.d. +0,066 |
| T=40 F1 | 3 | +0,060 | −0,047 s.d. +0,168 | +0,010 | −0,185 s.d. +0,205 |
| T=50 F1 | 3 | **+0,091** | +0,004 s.d. +0,179 | +0,036 | −0,048 s.d. +0,120 |
| T=60 F1 | 3 | +0,130 | −0,011 s.d. +0,270 | +0,028 | −0,002 s.d. +0,059 |

### 3.2 `leave_event_out`

**F1(std) per seed** (epoch terpilih dalam kurung)

| Eksperimen | n | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 | rata-rata ± sd | min – maks |
|---|---|---|---|---|---|---|---|---|
| T=10 F1 | 5 | 0,766 (14) | 0,835 (14) | 0,816 (9) | 0,737 (14) | 0,846 (9) | 0,800 ± 0,047 | 0,737 – 0,846 |
| T=10 F2 | 5 | 0,752 (14) | 0,874 (14) | 0,855 (14) | 0,842 (14) | 0,797 (14) | 0,824 ± 0,049 | 0,752 – 0,874 |
| T=10 F3 | 5 | 0,851 (9) | 0,859 (14) | 0,841 (14) | 0,867 (9) | 0,875 (9) | 0,858 ± 0,014 | 0,841 – 0,875 |
| T=30 F1 | 3 | 0,783 (4) | 0,851 (14) | 0,876 (14) | – | – | 0,837 ± 0,048 | 0,783 – 0,876 |
| T=40 F1 | 3 | 0,899 (14) | 0,922 (4) | 0,810 (14) | – | – | 0,877 ± 0,059 | 0,810 – 0,922 |
| T=50 F1 | 3 | 0,857 (14) | 0,920 (9) | 0,938 (14) | – | – | 0,905 ± 0,042 | 0,857 – 0,938 |
| T=60 F1 | 3 | 0,860 (14) | 0,905 (4) | 0,924 (14) | – | – | 0,896 ± 0,033 | 0,860 – 0,924 |
| T=30 F1 (30 ep) | 5 | 0,787 (29) | 0,851 (14) | 0,872 (29) | 0,847 (24) | 0,890 (9) | 0,849 ± 0,039 | 0,787 – 0,890 |
| T=30 F2 (30 ep) | 5 | 0,851 (29) | 0,860 (9) | 0,789 (24) | 0,903 (24) | 0,848 (29) | 0,850 ± 0,041 | 0,789 – 0,903 |
| T=10 F1 (30 ep) | 5 | 0,771 (19) | 0,857 (24) | 0,791 (29) | 0,760 (24) | 0,847 (19) | 0,805 ± 0,044 | 0,760 – 0,857 |
| T=10 F2 (30 ep) | 5 | 0,785 (24) | 0,874 (14) | 0,855 (24) | 0,842 (24) | 0,797 (24) | 0,831 ± 0,038 | 0,785 – 0,874 |
| T=10 F3 (30 ep) | 5 | 0,837 (19) | 0,859 (14) | 0,829 (29) | 0,821 (19) | 0,875 (9) | 0,844 ± 0,022 | 0,821 – 0,875 |
| T=30 F3 (30 ep) | 5 | 0,903 (29) | 0,879 (29) | 0,921 (24) | 0,923 (29) | 0,925 (19) | 0,910 ± 0,020 | 0,879 – 0,925 |

**HR@1(std) per seed** (epoch terpilih dalam kurung)

| Eksperimen | n | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 | rata-rata ± sd | min – maks |
|---|---|---|---|---|---|---|---|---|
| T=10 F1 | 5 | 0,566 (14) | 0,624 (14) | 0,759 (9) | 0,498 (14) | 0,461 (9) | 0,582 ± 0,118 | 0,461 – 0,759 |
| T=10 F2 | 5 | 0,419 (14) | 0,584 (14) | 0,525 (14) | 0,528 (14) | 0,609 (14) | 0,533 ± 0,073 | 0,419 – 0,609 |
| T=10 F3 | 5 | 0,588 (9) | 0,638 (14) | 0,619 (14) | 0,564 (9) | 0,613 (9) | 0,605 ± 0,029 | 0,564 – 0,638 |
| T=30 F1 | 3 | 0,477 (4) | 0,478 (14) | 0,595 (14) | – | – | 0,517 ± 0,068 | 0,477 – 0,595 |
| T=40 F1 | 3 | 0,608 (14) | 0,622 (4) | 0,498 (14) | – | – | 0,576 ± 0,068 | 0,498 – 0,622 |
| T=50 F1 | 3 | 0,504 (14) | 0,472 (9) | 0,641 (14) | – | – | 0,539 ± 0,090 | 0,472 – 0,641 |
| T=60 F1 | 3 | 0,480 (14) | 0,568 (4) | 0,539 (14) | – | – | 0,529 ± 0,045 | 0,480 – 0,568 |
| T=30 F1 (30 ep) | 5 | 0,507 (29) | 0,478 (14) | 0,609 (29) | 0,622 (24) | 0,586 (9) | 0,560 ± 0,064 | 0,478 – 0,622 |
| T=30 F2 (30 ep) | 5 | 0,646 (29) | 0,487 (9) | 0,556 (24) | 0,695 (24) | 0,574 (29) | 0,591 ± 0,081 | 0,487 – 0,695 |
| T=10 F1 (30 ep) | 5 | 0,535 (19) | 0,591 (24) | 0,708 (29) | 0,496 (24) | 0,530 (19) | 0,572 ± 0,083 | 0,496 – 0,708 |
| T=10 F2 (30 ep) | 5 | 0,390 (24) | 0,584 (14) | 0,604 (24) | 0,500 (24) | 0,610 (24) | 0,537 ± 0,094 | 0,390 – 0,610 |
| T=10 F3 (30 ep) | 5 | 0,567 (19) | 0,638 (14) | 0,599 (29) | 0,465 (19) | 0,613 (9) | 0,577 ± 0,067 | 0,465 – 0,638 |
| T=30 F3 (30 ep) | 5 | 0,591 (29) | 0,587 (29) | 0,545 (24) | 0,565 (29) | 0,707 (19) | 0,599 ± 0,063 | 0,545 – 0,707 |

**Rata-rata ± sd, semua ukuran (Test, std)**

| Eksperimen | n | F1 | Pre | Rec | HR@1 | HR@3 | s/epoch |
|---|---|---|---|---|---|---|---|
| T=10 F1 | 5 | 0,800 ± 0,047 | 0,720 ± 0,054 | 0,903 ± 0,071 | 0,582 ± 0,118 | 0,699 ± 0,103 | 58 |
| T=10 F2 | 5 | 0,824 ± 0,049 | 0,763 ± 0,050 | 0,898 ± 0,072 | 0,533 ± 0,073 | 0,638 ± 0,088 | 58 |
| T=10 F3 | 5 | 0,858 ± 0,014 | 0,793 ± 0,027 | 0,937 ± 0,019 | 0,605 ± 0,029 | 0,738 ± 0,019 | 60 |
| T=30 F1 | 3 | 0,837 ± 0,048 | 0,766 ± 0,038 | 0,922 ± 0,066 | 0,517 ± 0,068 | 0,622 ± 0,052 | 142 |
| T=40 F1 | 3 | 0,877 ± 0,059 | 0,806 ± 0,070 | 0,962 ± 0,041 | 0,576 ± 0,068 | 0,695 ± 0,073 | 197 |
| T=50 F1 | 3 | 0,905 ± 0,042 | 0,839 ± 0,066 | 0,983 ± 0,009 | 0,539 ± 0,090 | 0,652 ± 0,054 | 254 |
| T=60 F1 | 3 | 0,896 ± 0,033 | 0,819 ± 0,056 | 0,992 ± 0,003 | 0,529 ± 0,045 | 0,680 ± 0,036 | 310 |
| T=30 F1 (30 ep) | 5 | 0,849 ± 0,039 | 0,784 ± 0,033 | 0,928 ± 0,052 | 0,560 ± 0,064 | 0,651 ± 0,034 | 158 |
| T=30 F2 (30 ep) | 5 | 0,850 ± 0,041 | 0,772 ± 0,059 | 0,949 ± 0,041 | 0,591 ± 0,081 | 0,722 ± 0,083 | 143 |
| T=10 F1 (30 ep) | 5 | 0,805 ± 0,044 | 0,742 ± 0,064 | 0,882 ± 0,022 | 0,572 ± 0,083 | 0,687 ± 0,087 | 57 |
| T=10 F2 (30 ep) | 5 | 0,831 ± 0,038 | 0,783 ± 0,048 | 0,887 ± 0,051 | 0,537 ± 0,094 | 0,648 ± 0,096 | 57 |
| T=10 F3 (30 ep) | 5 | 0,844 ± 0,022 | 0,796 ± 0,016 | 0,900 ± 0,047 | 0,577 ± 0,067 | 0,720 ± 0,052 | 59 |
| T=30 F3 (30 ep) | 5 | 0,910 ± 0,020 | 0,872 ± 0,024 | 0,952 ± 0,026 | 0,599 ± 0,063 | 0,750 ± 0,058 | 145 |

Baris "(30 ep)" dilatih 30 epoch, jadi tidak dimasukkan ke tabel selisih terhadap T = 10 F1 (15 epoch) di bawah. Perbandingan antar fusion di dalam kelompok ini ada di bagian 5.10 (T = 30) dan 5.12 (T = 10). s/epoch F1 (30 ep) 158 termasuk seed 42 yang berjalan lambat (215 s/epoch, bagian 5.8); tanpa run itu 144.

**Selisih terhadap baseline T=10 F1** (rata-rata eksperimen − rata-rata baseline, CI 95% Welch; **tebal** = CI tidak memuat 0)

| Eksperimen | n | ΔF1(std) | CI 95% | ΔHR@1(std) | CI 95% |
|---|---|---|---|---|---|
| T=10 F2 | 5 | +0,024 | −0,046 s.d. +0,094 | −0,049 | −0,197 s.d. +0,099 |
| T=10 F3 | 5 | **+0,059** | +0,001 s.d. +0,116 | +0,023 | −0,121 s.d. +0,167 |
| T=30 F1 | 3 | +0,037 | −0,058 s.d. +0,131 | −0,065 | −0,226 s.d. +0,095 |
| T=40 F1 | 3 | +0,077 | −0,040 s.d. +0,194 | −0,006 | −0,167 s.d. +0,155 |
| T=50 F1 | 3 | **+0,105** | +0,021 s.d. +0,189 | −0,043 | −0,229 s.d. +0,143 |
| T=60 F1 | 3 | **+0,096** | +0,026 s.d. +0,167 | −0,052 | −0,199 s.d. +0,094 |


### 3.3 `random_original` (protokol bocor, tidak sebanding)

**F1(std) per seed** (epoch terpilih dalam kurung)

| Eksperimen | n | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 | rata-rata ± sd | min – maks |
|---|---|---|---|---|---|---|---|---|
| T=10 F1 (50 ep, pilih HR@1) | 3 | 0,924 (9) | 0,913 (9) | 0,931 (19) | – | – | 0,923 ± 0,009 | 0,913 – 0,931 |

**HR@1(std) per seed** (epoch terpilih dalam kurung)

| Eksperimen | n | seed 42 | seed 7 | seed 123 | seed 31 | seed 2026 | rata-rata ± sd | min – maks |
|---|---|---|---|---|---|---|---|---|
| T=10 F1 (50 ep, pilih HR@1) | 3 | 0,975 (9) | 0,961 (9) | 0,989 (19) | – | – | 0,975 ± 0,014 | 0,961 – 0,989 |

**Rata-rata ± sd, semua ukuran (Test, std)**

| Eksperimen | n | F1 | Pre | Rec | HR@1 | HR@3 | s/epoch |
|---|---|---|---|---|---|---|---|
| T=10 F1 (50 ep) | 3 | 0,923 ± 0,009 | 0,873 ± 0,006 | 0,980 ± 0,012 | 0,975 ± 0,014 | 0,979 ± 0,012 | 75 |

## 4. Gambar

![Semua eksperimen, per seed](Gambar_Seed_Semua.png)

Titik = satu seed, garis hitam = rata-rata. Biru = F1, oranye = F2, hijau = F3 (GMU). Di panel `leave_event_out` HR@1, titik-titik satu eksperimen membentang lebih lebar daripada jarak antar eksperimen, kecuali F3 yang titiknya rapat (0,564–0,638).

## 5. Pembacaan

### 5.1 Seberapa besar sebaran seed

| Skema | Ukuran | sd terkecil | sd terbesar | Eksperimen sd terbesar |
|---|---|---|---|---|
| `within_event` | F1(std) | 0,014 (T = 10 F1) | 0,064 (T = 10 F3) | T = 10 F3 (seed 123 = 0,729) |
| `within_event` | HR@1(std) | 0,010 (T = 30 F1) | 0,084 (T = 40) | T = 40 (seed 42 = 0,728) |
| `leave_event_out` | F1(std) | 0,014 (T = 10 F3) | 0,059 (T = 40) | T = 40 |
| `leave_event_out` | HR@1(std) | 0,029 (T = 10 F3) | 0,118 (T = 10 F1) | T = 10 F1 |

`leave_event_out` cenderung lebih tidak stabil untuk lokalisasi daripada `within_event` (sd 0,029–0,118 melawan 0,010–0,084). Pengecualiannya F3: sd HR@1 `leave_event_out` hanya 0,029, terkecil dari semua eksperimen, tetapi perbedaan sebaran terhadap F1 belum terbukti (Levene p = 0,09), dan di `within_event` sebaran F1(std) F3 justru terbesar. Alasan yang masuk akal: Test `leave_event_out` terdiri dari event yang tidak ada di Train, dan hasilnya sensitif pada bagaimana model kebetulan tertata. Ini dugaan, belum diperiksa per event.

### 5.2 Pengaruh T pada deteksi (F1(std))

- `within_event`: rata-rata naik dari 0,743 (T = 5) ke 0,892 (T = 60) dengan satu penurunan di T = 40 (0,823). Terhadap T = 10: T = 30 terbukti (+0,067, CI +0,040 s.d. +0,094, n = 5; dengan 3 seed dulu +0,082), T = 50 tipis (+0,091, CI +0,004 s.d. +0,179), T = 60 belum (+0,130, CI −0,011 s.d. +0,270 karena sd 0,059).
- `leave_event_out`: naik sampai T = 50 (0,905) lalu mendatar di T = 60 (0,896). T = 50 dan T = 60 terbukti terhadap T = 10 (+0,105 dan +0,096).
- Perhatikan bahwa T = 50 bisa tampak "terbukti" sedangkan T = 60 yang rata-ratanya lebih tinggi tidak. Itu karena lebar CI mengikuti sd tiap eksperimen, bukan karena T = 50 lebih baik. Jangan menyusun peringkat T dari ada-tidaknya tanda tebal.
- Kenaikan ini datang dari Recall (0,92 → 0,99 di T = 60) dan Precision (0,72 → 0,82 di `leave_event_out`). Alarm palsu tetap tinggi di T besar (lihat `Temuan_Data_dan_Sweep_T.md` bagian 16: FPR 0,47 ± 0,18 di T = 60 `leave_event_out`).

### 5.3 Pengaruh T pada lokalisasi (HR@1(std))

- `within_event`: hampir datar, 0,799–0,850, selisih terbesar terhadap T = 10 hanya +0,036. Tidak ada yang terbukti. T = 60 hampir (CI −0,002 s.d. +0,059).
- `leave_event_out`: 0,517–0,582, **tanpa tren** dan tanpa selisih terbukti. T = 10 paling tinggi secara rata-rata, tetapi dengan sd 0,118 itu tidak bisa dibedakan dari T lain.
- Artinya: kalau tujuannya menunjuk layanan penyebab, memperbesar T tidak menolong, sedangkan biaya latih per epoch di T = 60 sekitar 6× T = 10 (lihat `Temuan_Data_dan_Sweep_T.md` bagian 17).

### 5.4 F1 vs F2 vs F3 di T = 10

Rinciannya di `Laporan_Fusion_F1_vs_F2.md` bagian 9 (F1 vs F2) dan bagian 10 (F3), serta `docs/F3_GMU.md` bagian 13.

| Selisih (CI 95% Welch) | `within_event` F1(std) | `within_event` HR@1(std) | `leave_event_out` F1(std) | `leave_event_out` HR@1(std) |
|---|---|---|---|---|
| F2 − F1 | **+0,043** (+0,005 s.d. +0,081) | +0,030 | +0,024 | −0,049 |
| F3 − F1 | +0,045 (−0,033 s.d. +0,123) | **+0,042** (+0,008 s.d. +0,075) | **+0,059** (+0,001 s.d. +0,116) | +0,023 |
| F3 − F2 | +0,002 | +0,011 | +0,035 | +0,072 (−0,018 s.d. +0,161) |

- F3 unggul atas F1 di dua tempat, dan keduanya tipis. Di `within_event`, kenaikan HR@1 berasal dari Recall: HR@1 bersyarat (hanya gangguan yang terdeteksi) sama, 0,896 vs 0,890. Di `leave_event_out`, kenaikan F1(std) berasal dari Precision (+0,073), yaitu alarm palsu lebih sedikit (FPR 0,371 vs 0,535).
- F3 dan F2 tidak bisa dibedakan. Karena F3 punya 28% parameter lebih banyak dari F1 dan F2 punya 14% lebih sedikit, keunggulan F3 atas F1 belum bisa dikaitkan khusus pada gate per modalitas.

### 5.5 Pola per seed

Dengan tiga seed yang dipakai di semua eksperimen (42, 7, 123), peringkatnya tidak konsisten di `within_event`. Seed 42 rata-rata peringkat 2,25 dan 2,12 (harapan jika acak = 2,0) untuk F1(std) dan HR@1(std), dari 8 konfigurasi. Di `leave_event_out` ada petunjuk lemah: **seed 42 paling rendah di 5 dari 7 konfigurasi**, baik untuk F1(std) maupun HR@1(std) (rata-rata peringkat 2,71 untuk keduanya). Ini bisa kebetulan, karena hanya tiga seed dan ketujuh konfigurasi tidak saling bebas (T = 10 F1, F2, dan F3 memakai seed yang sama). Kalau memang ada efek seed yang menetap, perbandingan T seharusnya berpasangan per seed dan CI-nya akan lebih sempit. Itu belum dikerjakan.

### 5.6 Pilihan epoch

Epoch 4 terpilih di 9 run, semuanya di T ≠ 10: T = 5 seed 7, T = 30 `within_event` (F1 seed 7 dan 2026, F2 seed 42, F3 seed 123 dan 31), T = 30 `leave_event_out` seed 42, T = 40 `leave_event_out` seed 7, dan T = 60 `leave_event_out` seed 7. Di T = 10 tidak pernah. Di T = 30 `within_event`, 5 dari 15 run memilih epoch 4 dan hanya 1 memilih epoch 14, jadi di sana Val memuncak lebih awal, bukan terlambat (sejalan dengan bagian 5.8). Epoch 14 (terakhir) terpilih di banyak run T besar. Jadi pada T besar, kapan Val terbaik bervariasi lebar, dan 15 epoch mungkin belum cukup untuk membandingkan T secara adil (dugaan, belum diuji).

### 5.7 `random_original`

Hanya F1, T = 10, 3 seed: F1(std) 0,923 ± 0,009 dan HR@1(std) 0,975 ± 0,014. Sebaran seed sangat kecil. Protokol ini bocor (event yang sama muncul di Train dan Test), jadi hasilnya mendekati batas atas dan **tidak sebanding** dengan dua skema lainnya. Itu juga sebabnya sebarannya kecil.

### 5.8 Cek epoch: T = 30 dengan 30 epoch (24 November, seed 42, n = 1)

Tujuan: memeriksa apakah 15 epoch cukup di T = 30 sebelum perbandingan fusion dijalankan di T itu. Run: F1, seed 42, 30 epoch, evaluasi tiap 5 epoch, pemilihan epoch lewat Val `combo` (`work/result/a3b11e96`, `work/result/14f5c50b`, log `grid_T30_cek30.out`).

**Kurva Val `combo` dan training loss**

| Epoch | 4 | 9 | 14 | 19 | 24 | 29 |
|---|---|---|---|---|---|---|
| `within_event` Val combo | 0,945 | **0,960** | 0,944 | 0,947 | 0,933 | 0,937 |
| `within_event` training loss | 0,126 | 0,079 | 0,055 | 0,052 | 0,035 | 0,020 |
| `leave_event_out` Val combo | 0,753 | 0,745 | 0,750 | 0,760 | 0,766 | **0,790** |
| `leave_event_out` training loss | 0,098 | 0,050 | 0,036 | 0,027 | 0,011 | 0,019 |
| `leave_event_out` Test F1(std) / HR@1(std) | 0,783 / 0,477 | – | – | 0,792 / 0,509 | 0,759 / 0,478 | 0,787 / 0,507 |

Test hanya tercatat pada epoch yang Val-nya menjadi rekor baru.

**Seed 42 di semua T (Test, std, epoch terpilih lewat Val)**

| T | Epoch latih | WE epoch | WE F1 | WE FPR | WE HR@1 | WE HR@1 bersyarat | LEO epoch | LEO F1 | LEO FPR | LEO HR@1 | LEO HR@1 bersyarat |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 15 | 9 | 0,708 | 0,89 | 0,809 | 0,856 | – | – | – | – | – |
| 10 | 15 | 14 | 0,786 | 0,45 | 0,809 | 0,919 | 14 | 0,766 | 0,62 | 0,566 | 0,648 |
| 30 | 15 | 9 | 0,847 | 0,44 | 0,837 | 0,871 | 4 | 0,783 | 0,56 | 0,477 | 0,557 |
| **30** | **30** | **9** | **0,847** | **0,44** | **0,837** | **0,871** | **29** | **0,787** | **0,51** | **0,507** | **0,604** |
| 40 | 15 | 9 | 0,772 | 0,66 | 0,728 | 0,811 | 14 | 0,899 | 0,36 | 0,608 | 0,623 |
| 50 | 15 | 14 | 0,817 | 0,69 | 0,892 | 0,913 | 14 | 0,857 | 0,59 | 0,504 | 0,516 |
| 60 | 15 | 14 | 0,930 | 0,25 | 0,847 | 0,855 | 14 | 0,860 | 0,67 | 0,480 | 0,483 |

WE = `within_event`, LEO = `leave_event_out`. Satu seed per T, jadi peringkat antar T di tabel ini tidak boleh dipakai (seed 42 sering jauh dari rata-rata, misalnya HR@1 WE T = 40: 0,728 vs rata-rata 0,824). Run uji lama T = 10 dengan 30 epoch di LEO tidak dimasukkan karena memakai kriteria pemilihan dan jadwal evaluasi yang berbeda.

**Biaya.** Tercatat 186 s/epoch (WE) dan 215 s/epoch (LEO), 98 dan 114 menit per run. Itu sekitar 50% lebih lambat dari run T = 30 sebelumnya (124 dan 142 s/epoch) secara merata di semua epoch, kemungkinan karena mode daya laptop (belum dipastikan). Dengan kecepatan normal, satu run 30 epoch di T = 30 diperkirakan 66 dan 76 menit, hampir sama dengan 15 epoch di T = 50.

Pembacaan:
1. **`within_event`: 15 epoch cukup.** Val memuncak di epoch 9, lalu turun sementara training loss terus turun (overfit). Run 30 epoch memilih epoch 9 dan hasil Test-nya identik dengan run 15 epoch.
2. **`leave_event_out`: Val masih naik sampai epoch 29**, tetapi Test hampir tidak ikut: F1(std) +0,004, HR@1 +0,030, HR@1 bersyarat +0,047, FPR −0,05, Recall −0,016, semuanya jauh di bawah sebaran antar seed (sd HR@1 ±0,07). Ini konsisten dengan temuan bahwa Val `leave_event_out` tidak meramalkan Test (`Laporan_Fusion_F1_vs_F2.md` bagian 9.4).
3. **Lokalisasi T = 30 yang rendah di LEO bukan karena kurang epoch.** Dengan 30 epoch pun HR@1 seed 42 (0,507) masih di bawah T = 10 (0,566).
4. **Keputusan untuk perbandingan fusion di T = 30:** `within_event` 15 epoch, `leave_event_out` 30 epoch. Epoch sama untuk semua fusion di dalam satu (T, skema), sehingga perbandingan fusion tetap adil. Akibatnya, run fusion `leave_event_out` T = 30 tidak bisa dipakai untuk membandingkan T (epoch berbeda dari sweep T).

### 5.9 F1 vs F2 vs F3 di T = 30, `within_event` (24 November, n = 5)

Rinciannya di `Laporan_Fusion_F1_vs_F2.md` bagian 11. Data `A1_T30`, 15 epoch (cukup menurut bagian 5.8), seed 42, 7, 123, 31, 2026. Keluaran: `grid_T30_15ep_we.out`.

| Selisih (CI 95% Welch) | F1(std) | Precision(std) | HR@1(std) | FPR | HR@1 bersyarat |
|---|---|---|---|---|---|
| F2 − F1 | +0,009 (−0,022 s.d. +0,041) | +0,017 | −0,005 | −0,047 | −0,002 |
| F3 − F1 | +0,035 (−0,025 s.d. +0,095) | +0,073 (−0,029 s.d. +0,175) | +0,004 | −0,171 (−0,409 s.d. +0,068) | **+0,023** (+0,003 s.d. +0,043) |
| F3 − F2 | +0,026 | +0,057 | +0,009 | −0,124 | **+0,024** (+0,005 s.d. +0,044) |

Rata-rata: F1(std) 0,829 / 0,839 / 0,865 dan HR@1(std) 0,833 / 0,828 / 0,837 untuk F1 / F2 / F3. Waktu latih 125 / 125 / 127 s/epoch.

- **F1 dan F2 tidak bisa dibedakan.** Petunjuk F2 di T = 10 (+0,043) tinggal +0,009.
- **F3 cenderung lebih sedikit alarm palsu** (FPR 0,36 vs 0,53), tetapi sangat bergantung seed: 0,20–0,29 di tiga seed, 0,66 di seed 2026.
- **HR@1 bersyarat F3 sedikit lebih tinggi** (+0,02, tipis), tetapi Recall-nya sedikit lebih rendah, sehingga HR@1 biasa setara. Di T = 10 polanya terbalik (Recall lebih tinggi, HR@1 bersyarat sama).
- **Tidak ada selisih fusion `within_event` yang lolos di T = 10 dan T = 30 sekaligus.** Untuk deteksi, efek T (+0,07 s.d. +0,10 untuk ketiga fusion terhadap T = 10 F1) lebih besar dari efek fusion di T = 30 (paling besar +0,035).

### 5.10 F1 vs F2 vs F3 di T = 30, `leave_event_out` (25 November, n = 5, 30 epoch)

Rinciannya di `Laporan_Fusion_F1_vs_F2.md` bagian 12. Data `A1_T30`, **30 epoch** (bagian 5.8), seed 42, 7, 123, 31, 2026. Keluaran: `grid_T30_30ep_leo.out`. Test: 16.932 jendela gangguan, 9.880 normal.

| Selisih (CI 95% Welch) | F1(std) | Precision(std) | HR@1(std) | HR@3(std) | FPR | HR@1 bersyarat |
|---|---|---|---|---|---|---|
| F2 − F1 | +0,001 (−0,058 s.d. +0,059) | −0,012 | +0,031 | +0,070 | +0,053 | +0,021 |
| F3 − F1 | **+0,061** (+0,013 s.d. +0,109) | **+0,089** (+0,046 s.d. +0,131) | +0,039 (−0,054 s.d. +0,131) | **+0,099** (+0,026 s.d. +0,171) | **−0,199** (−0,287 s.d. −0,111) | +0,026 |
| F3 − F2 | **+0,060** (+0,010 s.d. +0,110) | **+0,101** (+0,028 s.d. +0,173) | +0,008 | +0,028 | **−0,252** (−0,461 s.d. −0,043) | +0,005 |

Rata-rata F1 / F2 / F3: F1(std) 0,849 / 0,850 / 0,910, HR@1(std) 0,560 / 0,591 / 0,599, FPR 0,439 / 0,492 / 0,240. Waktu latih 144 (tanpa run lambat) / 143 / 145 s/epoch.

- **F3 mendeteksi lebih baik dari F1 dan F2.** F1(std) F3 lebih tinggi dari keduanya di kelima seed. Sumbernya Precision, bukan Recall (Recall 0,93–0,95 di ketiga fusion).
- **Alarm palsu F3 sekitar separuhnya.** FPR tertinggi F3 (0,33) masih di bawah FPR terendah F1 (0,36). Uji permutasi memberi p = 0,008, nilai terkecil yang mungkin dengan 5 lawan 5.
- **Lokalisasi tidak berbeda.** HR@1 dan HR@1 bersyarat setara. HR@3 F3 lebih tinggi dari F1 (+0,099), tetapi tidak dari F2. Ini dibaca sebagai petunjuk.
- **F2 setara F1** di semua ukuran.
- **Berulang lintas T:** F3 − F1 di T = 10 `leave_event_out` juga lolos untuk F1(std) (+0,059) dan FPR (−0,164). Di T = 30 besarnya hampir sama (+0,061, −0,199). Di `within_event` arahnya sama tetapi tidak terbukti.
- 7 dari 24 selisih lolos, jauh di atas 1–2 yang diharapkan dari kebetulan. Karena F1(std), Precision, dan FPR mengukur gejala yang sama, ini dihitung sebagai satu temuan (alarm palsu) ditambah satu petunjuk (HR@3).
- **Catatan:** 7 dari 15 run memilih epoch 29 (terakhir), termasuk 3 dari 5 run F3. Angka mungkin masih bergeser dengan epoch lebih banyak.

### 5.11 F1w: kontrol kapasitas (26 November, n = 5)

Rinciannya (desain, hash, per seed, efisiensi) di `Laporan_Fusion_F1_vs_F2.md` bagian 13. Alasan eksperimen: F3 punya parameter fusion 2× F1, sehingga keunggulannya di bagian 5.10 bisa berasal dari kapasitas, bukan dari arsitektur GMU. F1w (`concat_glu_wide`) = F1 dengan satu lapisan tersembunyi tambahan (Linear 144 → 135, ReLU), GLU tetap. Parameter fusion 36.983 vs F3 36.864. Pengaturan sama dengan F1/F2/F3 pada setting yang sama. Keluaran: `grid_T10_f1w_leo.out`, `grid_T10_f1w_we.out`, `grid_T30_f1w_leo.out`. Tabel per seed di bagian 3 belum memuat F1w.

F1w − F1 = efek kapasitas. F3 − F1w = efek arsitektur pada kapasitas sama.

| Setting | Metrik | F1 | F1w | F3 | F1w − F1 | F3 − F1w (CI 95% Welch) |
|---|---|---|---|---|---|---|
| T = 10 `within_event` | F1(std) | 0,763 | 0,778 | 0,808 | +0,016 | +0,030 (−0,050 s.d. +0,109) |
| | HR@1(std) | 0,814 | 0,836 | 0,856 | +0,022 | +0,020 (−0,044 s.d. +0,085) |
| | FPR | 0,618 | 0,601 | 0,534 | −0,017 | −0,067 (−0,363 s.d. +0,228) |
| T = 10 `leave_event_out` | F1(std) | 0,800 | 0,855 | 0,858 | +0,055 (−0,002 s.d. +0,113) | +0,003 (−0,022 s.d. +0,029) |
| | HR@1(std) | 0,582 | 0,667 | 0,605 | +0,085 | **−0,062** (−0,118 s.d. −0,006) |
| | FPR | 0,535 | 0,439 | 0,371 | −0,097 | −0,067 (−0,182 s.d. +0,047) |
| T = 30 `leave_event_out` (30 epoch) | F1(std) | 0,849 | 0,850 | 0,910 | +0,001 | **+0,060** (+0,010 s.d. +0,110) |
| | HR@1(std) | 0,560 | 0,559 | 0,599 | −0,002 | +0,040 (−0,054 s.d. +0,135) |
| | FPR | 0,439 | 0,438 | 0,240 | −0,001 | **−0,199** (−0,340 s.d. −0,057) |

- **T = 30 `leave_event_out`: arsitektur.** Kapasitas tambahan tidak mengubah F1 sama sekali, sedangkan F3 tetap unggul atas F1w dengan besar yang sama seperti atas F1 (bagian 5.10). Precision (+0,087) dan HR@3 (+0,089) juga lolos.
- **T = 10: kapasitas.** F1w menyamai F3 dalam deteksi. Di `leave_event_out`, F1w lebih tinggi untuk HR@1. NDCG@3 dan HR@1 bersyarat searah dengan p = 0,048, jadi indikasi.
- **Biaya:** F1w praktis sama dengan F1 (+0–2% inferensi, +0% latih). F3 +5–7% di T = 10 dan +1–2% di T = 30 terhadap F1.
- ~~**Belum terpisah:** T = 10 `leave_event_out` memakai 15 epoch, T = 30 memakai 30 epoch. Jadi "GMU unggul di T besar" bisa juga berarti "GMU unggul bila dilatih lebih lama".~~ Sudah dipisahkan di bagian 5.12.

### 5.12 Kontrol epoch: T = 10 `leave_event_out` dengan 30 epoch (27 November, n = 5)

Rinciannya (hash, per seed, efisiensi) di `Laporan_Fusion_F1_vs_F2.md` bagian 14. Tujuan: memisahkan efek T dari efek lama training pada temuan bagian 5.11. F1, F1w, F2, F3, 5 seed, 30 epoch, pengaturan lain sama. Keluaran: `grid_T10_30ep_leo.out`. Run lama `d574273b` (F1 seed 42, 30 epoch, pemilihan lewat `HR@1`) tidak dihitung: `banding_fusion.py` sekarang hanya mengambil run `select_metric = combo`.

**30 epoch vs 15 epoch** (fusion yang sama, CI 95% Welch, p permutasi):

| Fusion | F1(std) 15 ep | F1(std) 30 ep | Selisih | FPR 15 ep | FPR 30 ep | Selisih |
|---|---|---|---|---|---|---|
| F1 | 0,800 | 0,805 | +0,005 (−0,061 s.d. +0,072), p = 0,87 | 0,535 | 0,471 | −0,065, p = 0,48 |
| F1w | 0,855 | 0,853 | −0,002 (−0,035 s.d. +0,031), p = 0,82 | 0,439 | 0,384 | −0,054, p = 0,25 |
| F2 | 0,824 | 0,831 | +0,007 (−0,058 s.d. +0,072), p = 0,75 | 0,425 | 0,377 | −0,049, p = 0,51 |
| F3 | 0,858 | 0,844 | −0,014 (−0,042 s.d. +0,014), p = 0,26 | 0,371 | 0,348 | −0,023, p = 0,56 |

**Antar fusion di 30 epoch:** tidak ada selisih yang CI-nya lepas dari 0, kecuali Recall F1w − F1 (+0,052, p = 0,056). F3 − F1w: F1(std) −0,009 (p = 0,59), FPR −0,036 (p = 0,19), HR@1 −0,073 (p = 0,10). F3 − F1 F1(std) turun dari +0,059 (lolos, 15 epoch) menjadi +0,039 (p = 0,12).

**T = 10 vs T = 30, sama-sama 30 epoch** (Test berbeda, deskriptif):

| Fusion | F1(std) T = 10 | F1(std) T = 30 | FPR T = 10 | FPR T = 30 |
|---|---|---|---|---|
| F1 | 0,805 | 0,849 | 0,471 | 0,439 |
| F1w | 0,853 | 0,850 | 0,384 | 0,438 |
| F2 | 0,831 | 0,850 | 0,377 | 0,492 |
| F3 | 0,844 | **0,910** | 0,348 | **0,240** |

- **15 epoch cukup di T = 10 `leave_event_out`.** Tidak ada fusion yang berubah. Epoch terpilih tersebar 9–29. Biaya dua kali lipat (±32 menit per run) tanpa perbaikan.
- **Keunggulan GMU atas F1w bergantung pada T, bukan epoch.** Pada epoch yang sama, F3 − F1w berubah dari −0,009 (T = 10) ke +0,060 (T = 30) untuk F1(std). F1w tidak mendapat apa-apa dari jendela yang lebih panjang, F3 paling banyak terbantu. Baru dua titik T.
- **Pengecualian lokalisasi melemah:** F1w > F3 untuk HR@1 di T = 10 tetap searah, tetapi p = 0,10 (15 epoch: 0,024). Indikasi saja.

## 6. Yang berubah dibanding laporan sebelumnya

Baseline T = 10 F1 sekarang berisi 5 seed (dulu 3), dan F3 (GMU, 5 seed) ditambahkan pada 23 November. Akibatnya CI selisih terhadap T = 10 berubah:

| Selisih terhadap T = 10 F1 | Dulu (n = 3) | Sekarang (n = 5) |
|---|---|---|
| `within_event` T = 30, F1(std) | +0,077 (CI +0,031 s.d. +0,123), terbukti | +0,082 (CI +0,061 s.d. +0,102), terbukti |
| `within_event` T = 50, F1(std) | belum terbukti | +0,091 (CI +0,004 s.d. +0,179), **tipis** |
| `leave_event_out` T = 50, F1(std) | belum terbukti | +0,105 (CI +0,021 s.d. +0,189), terbukti |
| `leave_event_out` T = 60, F1(std) | belum terbukti | +0,096 (CI +0,026 s.d. +0,167), terbukti |
| `within_event` T = 30, F1(std), dengan seed 31 dan 2026 di T = 30 (24 November) | +0,082 (n = 3 di T = 30) | +0,067 (CI +0,040 s.d. +0,094), tetap terbukti |

Rata-rata selisihnya hampir tidak berubah. Yang berubah adalah CI: baseline T = 10 yang punya sd kecil (0,014 di `within_event`) dan n = 5 menyempitkan lebar CI. Itu sah, tetapi ini juga artinya status "belum terbukti" di laporan lama sebagian adalah akibat n kecil. Laporan lain (`Temuan_Data_dan_Sweep_T.md` bagian 13–16, `Ringkasan_Sweep_T_untuk_Dosen.md`) masih memakai CI n = 3 dan belum diperbarui.

## 7. Keterbatasan

1. **Jumlah seed tidak seimbang** (5 vs 3). CI di T selain 10 lebar, dan seed 31 dan 2026 belum ada di sana, kecuali T = 30 `within_event`. Dua seed tambahan di T = 30 menurunkan rata-rata F1(std) F1 dari 0,844 ke 0,829, contoh bahwa rata-rata 3 seed bisa bergeser 0,015.
2. **Banyak perbandingan tanpa koreksi:** 30 selisih terhadap T = 10 F1, 9 melewati batas (dua tambahan, T = 30 F2 dan F3 F1(std), bercampur efek T dan fusion). Ditambah 24 selisih antar fusion di T = 30 `within_event` (bagian 5.9), 2 melewati batas, dan 24 di T = 30 `leave_event_out` (bagian 5.10), 7 melewati batas (saling berkaitan, satu temuan alarm palsu). Bila semuanya nol sebenarnya, kira-kira 1–2 yang melewati batas karena kebetulan. Tiga yang tipis (T = 50 `within_event`, F2 `within_event`, dan F3 `leave_event_out` F1(std)) paling mungkin kebetulan.
3. **Test set berbeda antar T**, jadi selisih antar T tidak murni efek T.
4. **Seed hanya memengaruhi inisialisasi dan urutan batch.** Event Test tetap, sehingga sebaran ini tidak mencakup variasi akibat event yang dipilih.
5. **15 epoch untuk semua T**, dan 5 run memilih epoch 4. Pada T besar, 15 epoch mungkin tidak adil. Di T = 30 sudah dicek dengan 30 epoch (bagian 5.8, n = 1): cukup untuk `within_event`, belum untuk `leave_event_out` menurut Val, tetapi Test hampir tidak berubah. T = 40–60 belum dicek.
6. **Fusion hanya F1, F2, F3, di T = 10 dan T = 30 (kedua skema).** Di T = 30 `leave_event_out` dipakai 30 epoch, sehingga kelompok itu tidak setara dengan sweep T. F4 belum dikerjakan dan harus memakai kelima seed. Kapasitas antar fusion tidak sama (F2 −14%, F3 +28% parameter terhadap F1), sehingga selisih fusion bercampur dengan efek kapasitas. Untuk F3 sudah dikontrol dengan F1w (bagian 5.11) di T = 10 dan T = 30 `leave_event_out`, tetapi belum di T = 30 `within_event`. Epoch T = 10 `leave_event_out` sudah disamakan dengan T = 30 (bagian 5.12), tetapi Test tetap berbeda antar T.
7. **Tidak ada ablation modalitas dan tidak ada analisis per jenis gangguan.**

## 8. Yang boleh dan belum boleh diklaim

**Boleh:**
- Menambah T dari 10 ke 30 menaikkan F1(std) `within_event` (+0,067, n = 5, CI tidak memuat 0). Kenaikan serupa terjadi untuk ketiga fusion.
- Di `leave_event_out`, T = 50 dan 60 menaikkan F1(std) sekitar 0,10 terhadap T = 10.
- Tidak ada bukti bahwa T besar memperbaiki lokalisasi (HR@1(std)) di skema mana pun.
- F1 dan F2 tidak bisa dibedakan secara meyakinkan di T = 10.
- F3 (GMU) setara atau sedikit lebih baik dari F1 di T = 10: semua selisih rata-rata searah menguntungkan F3, dua di antaranya dengan CI tidak memuat 0 (tipis).
- Di T = 30 `within_event`, F1, F2, F3 setara untuk deteksi dan lokalisasi.
- Di T = 30 `leave_event_out`, F3 mendeteksi lebih baik dari F1 dan F2 (F1(std) +0,06) karena alarm palsunya jauh lebih sedikit (FPR 0,24 vs 0,44 / 0,49, di kelima seed).
- Terhadap F1, F3 mengurangi alarm palsu di `leave_event_out` pada T = 10 dan T = 30.
- F2 setara F1 di semua kondisi yang diuji (2 T × 2 skema).
- Di T = 30 `leave_event_out`, keunggulan F3 berasal dari arsitektur GMU, bukan dari kapasitas (F1w = F1, F3 > F1w).
- Di T = 10, keunggulan F3 atas F1 cukup dijelaskan oleh kapasitas (F1w ≈ F3), juga dengan 30 epoch.
- Keunggulan GMU atas F1w di `leave_event_out` bergantung pada T (ada di T = 30, tidak ada di T = 10), bukan pada lama training (bagian 5.12). Catatan: baru dua titik T.
- 15 epoch cukup untuk T = 10 `leave_event_out` (30 epoch tidak mengubah fusion mana pun).

**Belum boleh:**
- Menyebut satu T sebagai "terbaik". Selisih antar T besar (30–60) tidak terbukti.
- Menyebut F2 lebih baik dari F1 (satu petunjuk tipis di T = 10, tidak berulang di T = 30).
- Menyebut F3 lebih sedikit alarm palsu di T = 30 **`within_event`** (FPR 0,36 vs 0,53, CI memuat 0, sangat bergantung seed).
- Menyebut F3 "lebih baik" secara umum. Keunggulannya terbatas pada deteksi di `leave_event_out`. Lokalisasi tidak membaik, dan di `within_event` tidak ada yang terbukti.
- Menyebut keunggulan F3 berasal khusus dari **gating adaptif** per modalitas. Kapasitas sudah dipisahkan (bagian 5.11), tetapi GMU juga berbeda dari F1w dalam proyeksi terpisah per modalitas dan penjumlahan berbobot. Nilai gate belum dianalisis.
- Menyebut keunggulan GMU **makin besar** seiring T. Baru ada T = 10 dan T = 30 (`Jurnal_Eksperimen.md` R5).
- Menyebut F3 lebih stabil antar seed (Levene p ≈ 0,09 di T = 10 dan 0,41 di T = 30 `leave_event_out`; di `within_event` justru lebih tersebar).
- Membandingkan angka absolut T = 30 `leave_event_out` (30 epoch) dengan T lain yang dilatih 15 epoch. Pembanding T = 10 dengan 30 epoch sekarang ada (bagian 5.12).
- Menyebut efek T murni, karena Test berbeda per T.
- Menyebut seed 42 "jelek" di `leave_event_out` (petunjuk lemah, n = 3).

## 9. Reproduksi

```bash
cd "/home/ojan/AI Labs/EADRO - APDM"
work/envs/train312/bin/python -I pipeline/rekap_semua.py --gambar > Report/tabel_semua_eksperimen.md   # opsional
work/envs/train312/bin/python -I pipeline/banding_fusion.py                                           # F1/F2/F3 T = 10 (FPR, HR@1 bersyarat, uji permutasi)
work/envs/train312/bin/python -I pipeline/banding_fusion.py 30 15 within_event                        # F1/F2/F3 T = 30 `within_event`
work/envs/train312/bin/python -I pipeline/banding_fusion.py 30 30 leave_event_out                     # F1/F2/F3 T = 30 `leave_event_out` (30 epoch)
work/envs/train312/bin/python -I pipeline/banding_fusion.py 10 30 leave_event_out                     # kontrol epoch T = 10 (30 epoch)
```

`banding_fusion.py` otomatis menambahkan F1w (F1w − F1 dan F3 − F1w) bila run `concat_glu_wide` ada pada setting itu.

Skrip membaca `work/result/*/params.json` dan `running.log`, mengambil Test pada epoch yang terpilih lewat Val, lalu menghitung rata-rata, sd (n−1), dan CI Welch. Kelompok dengan n < 2 dilewati.
