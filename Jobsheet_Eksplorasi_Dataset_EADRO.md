# Jobsheet: Eksplorasi Dataset Train Ticket (EADRO)

Mata kuliah APDM. Dibuat 19 November 2026.

## Tujuan

Setelah mengerjakan jobsheet ini, kamu bisa:

1. Menjelaskan isi dataset mentah Train Ticket (TT): ada apa saja, formatnya seperti apa, dan berapa besarnya.
2. Membaca tiga modalitas (metrics, logs, traces) dan label fault langsung dari file mentah.
3. Menemukan sendiri masalah data yang sudah kita koreksi di pipeline: waktu bergeser 8 jam, span terduplikasi, span basi di luar run, dan trace yang jarang.
4. Melihat bagaimana sebuah fault tampak di ketiga modalitas pada waktu yang sama.
5. Memahami bagaimana data mentah diubah menjadi sampel EADRO (window T detik plus label).

## Persiapan

- Kerjakan di Jupyter Notebook baru di dalam folder proyek, misalnya `EDA/Jobsheet_EDA.ipynb`. Tiap blok kode di bawah ditulis untuk satu sel. Langkah 0 otomatis pindah ke root proyek, jadi notebook boleh berada di subfolder.
- Kernel: environment `work/envs/train312` (sudah ada pandas, numpy, matplotlib). Python lain dengan tiga library itu juga bisa. Kode sudah diuji di Python 3.8 (`preproc38`) dan 3.12 (`train312`).
- Jalankan sel **berurutan dari atas**. Banyak sel memakai variabel dari sel sebelumnya (`faults`, `fr`, `L`, `S`, `client`, dan lain-lain). Kalau kernel di-restart, ulangi dari Langkah 0.
- Data yang dibutuhkan:
  - `TT Dataset/TT Dataset/data/`: 9 run berisi fault beserta file labelnya.
  - `work/raw_nofault/`: 3 run normal (hasil ekstrak arsip `.tar.xz` dan `.txz` dari `TT Dataset/TT Dataset/no fault/`).
- Seluruh jobsheet butuh sekitar 1 sampai 1,5 jam. Tiap sel paling lama beberapa detik, karena yang dibaca hanya satu run.

Angka di bagian **Hasil yang diharapkan** didapat dari menjalankan kode ini pada data di laptop kamu. Kalau angkamu berbeda, berarti ada yang salah, entah di kode atau di datanya.

---

## Langkah 0. Import dan path

```python
import os, glob, json, re
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

# Pindah ke root proyek (folder yang berisi "TT Dataset"), supaya notebook bisa disimpan di subfolder mana pun
root = os.path.abspath(os.getcwd())
while not os.path.isdir(os.path.join(root, "TT Dataset")):
    if os.path.dirname(root) == root:
        raise FileNotFoundError("Folder 'TT Dataset' tidak ditemukan. Simpan notebook di dalam folder proyek EADRO.")
    root = os.path.dirname(root)
os.chdir(root)
print("Root proyek:", root)

DATA_DIR = "TT Dataset/TT Dataset/data"   # 9 run berfault + file label
NOFAULT_DIR = "work/raw_nofault"          # 3 run normal (hasil ekstrak)
SHIFT = 8 * 3600                          # selisih waktu spans/logs vs metrics (dibuktikan di Langkah A4)
```

---

# Bagian A. Gambaran Dataset Mentah

## A1. Struktur folder

Dataset ini terdiri dari beberapa **run**. Satu run adalah satu sesi rekaman sistem Train Ticket. Selama sesi itu, beberapa fault disuntikkan satu per satu, dan semua data monitoring direkam.

```python
fault_runs = sorted(d for d in glob.glob(f"{DATA_DIR}/TT.2*") if os.path.isdir(d))
nofault_runs = sorted(os.path.dirname(p)
                      for p in glob.glob(f"{NOFAULT_DIR}/**/spans.json", recursive=True))

print("Run berfault :", len(fault_runs))
print("Run normal   :", len(nofault_runs))

RUN = fault_runs[0]            # run yang dipakai untuk eksplorasi detail
print("\nIsi satu run:", RUN)
for f in sorted(os.listdir(RUN)):
    p = os.path.join(RUN, f)
    if os.path.isdir(p):
        print(f"  {f}/  ({len(os.listdir(p))} file)")
    else:
        print(f"  {f}  ({os.path.getsize(p)/1e6:.1f} MB)")
```

**Hasil yang diharapkan:**

```
Run berfault : 9
Run normal   : 3

Isi satu run: TT Dataset/TT Dataset/data/TT.2022-04-17T212101D2022-04-17T230842
  logs.json  (1.7 MB)
  metrics/  (27 file)
  spans.json  (42.8 MB)
```

**Penjelasan:**

| File | Modalitas | Isi |
|---|---|---|
| `metrics/<service>.csv` | Metrics | 1 file per service, 27 service. Nilai CPU, memori, dan jaringan tiap detik |
| `logs.json` | Logs | Dictionary `{service: [baris log, ...]}` |
| `spans.json` | Traces | List trace dari Jaeger. Satu trace = satu request yang melewati beberapa service |
| `TT.fault-<nama run>.json` (di luar folder run) | Label | Daftar fault yang disuntikkan: service, jenis, waktu mulai, durasi |

Nama folder seperti `2022-04-17T212101D2022-04-17T230842` berarti "mulai ... sampai ...". Jamnya **tidak** sama dengan jam UTC di dalam file. Jadi jangan pakai nama folder sebagai acuan waktu. Pakai `start` dan `end` di file label.

**Tugas A1:** File mana yang paling besar? Kenapa menurutmu trace jauh lebih besar dari log? (Petunjuk: lihat A5.)

---

## A2. Label fault

```python
rows = []
for r in fault_runs:
    name = os.path.basename(r)                                   # TT.2022-04-17T212101D...
    label = json.load(open(f"{DATA_DIR}/TT.fault-{name[3:]}.json"))
    for i, f in enumerate(label["faults"]):
        service = f["name"].replace("dockercomposemanifests_", "").rsplit("_", 1)[0]
        rows.append(dict(run=name[3:20], urutan=i, service=service, fault=f["fault"],
                         start=f["start"], durasi=f["duration"],
                         run_start=label["start"], run_end=label["end"]))
faults = pd.DataFrame(rows)

print("Jumlah fault:", len(faults))
print(faults.fault.value_counts(), "\n")
print("Service berbeda yang di-fault:", faults.service.nunique())
faults.head(9)
```

Contoh isi file label mentahnya:

```json
{
  "start": 1650172861.377429,
  "faults": [
    {"name": "dockercomposemanifests_ts-food-service_1", "fault": "cpu_load",
     "start": 1650172864.064904, "duration": 600},
    ...
  ],
  "end": 1650179322.9
}
```

Waktu ditulis dalam **detik Unix (epoch, UTC)**. `name` adalah nama container Docker, jadi awalan `dockercomposemanifests_` dan akhiran `_1` perlu dibuang supaya tersisa nama service.

```python
# Apakah setiap service mendapat ketiga jenis fault?
print(pd.crosstab(faults.service, faults.fault).describe().loc[["min", "max"]], "\n")

# Durasi fault dan jeda antar fault
faults["jeda_ke_berikut"] = faults.groupby("run").start.shift(-1) - (faults.start + faults.durasi)
print("Durasi fault (detik):", faults.durasi.unique())
print("Jeda antar fault (detik):", faults.jeda_ke_berikut.describe()[["min", "mean", "max"]].round(1).to_dict())

lama_run = faults.groupby("run").first().eval("(run_end - run_start) / 3600")
print("Lama satu run (jam):", lama_run.round(3).unique())
```

**Hasil yang diharapkan:**

- 81 fault = 9 run × 9 fault.
- Ada tiga jenis fault, masing-masing 27: `cpu_load`, `network_delay`, `network_loss`.
- 27 service berbeda di-fault. **Setiap service tepat sekali untuk tiap jenis fault** (crosstab min = max = 1).
- Setiap fault berdurasi tepat **600 detik** (10 menit). Jeda antar fault sekitar **114 sampai 124 detik**.
- Satu run berlangsung sekitar **1,79 jam**.

Polanya: di setiap run, 3 service di-fault berurutan, masing-masing dengan 3 jenis fault. Jadi `cpu_load`, `network_delay`, `network_loss` untuk service A, lalu tiga jenis yang sama untuk service B, dan seterusnya.

### Visualisasi timeline

```python
warna = {"cpu_load": "tab:orange", "network_delay": "tab:blue", "network_loss": "tab:purple"}
fig, ax = plt.subplots(figsize=(13, 4.5))
for y, (run, g) in enumerate(faults.groupby("run")):
    t0 = g.run_start.iloc[0]
    ax.barh(y, (g.run_end.iloc[0] - t0) / 60, left=0, color="#eee", edgecolor="#ccc")
    for _, f in g.iterrows():
        ax.barh(y, f.durasi / 60, left=(f.start - t0) / 60, color=warna[f.fault])
        ax.text((f.start - t0 + f.durasi / 2) / 60, y, re.sub(r"^ts-|-service$", "", f.service),
                ha="center", va="center", fontsize=6, color="white")
ax.set_yticks(range(faults.run.nunique()), sorted(faults.run.unique()))
ax.set_xlabel("menit sejak run mulai")
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in warna.values()], labels=list(warna),
          loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=8)
ax.set_title("Timeline fault di 9 run (abu-abu = tidak ada fault)")
plt.tight_layout(); plt.show()
```

**Yang perlu diamati:** bagian abu-abu (normal) di run berfault sangat sempit. Hampir seluruh run berisi fault. Ini penting di B4.

**Tugas A2:** Hitung berapa persen waktu sebuah run yang berada di dalam fault. (Petunjuk: 9 × 600 detik dibagi lama run.)

---

## A3. Metrics

```python
m = pd.read_csv(f"{RUN}/metrics/ts-food-service.csv")
print(m.shape)
print(m.head(3), "\n")
print("Selisih timestamp berturut-turut:", m.timestamp.diff().value_counts().to_dict())
print("Jumlah NaN:", int(m.isna().sum().sum()))
m.describe().T[["mean", "std", "min", "max"]]
```

**Hasil yang diharapkan:**

- 6.461 baris × 8 kolom: `timestamp` + 7 metrik.
- Timestamp naik tepat **1 detik** tiap baris. Tidak ada NaN.

| Kolom | Arti |
|---|---|
| `cpu_usage_system`, `cpu_usage_user`, `cpu_usage_total` | Pemakaian CPU container (mode kernel, mode user, total) |
| `memory_usage`, `memory_working_set` | Pemakaian memori (dalam fraksi, nilainya sangat kecil) |
| `rx_bytes`, `tx_bytes` | Byte jaringan yang diterima dan dikirim per detik |

```python
# Apakah semua 27 file seragam?
ringkas = []
for p in sorted(glob.glob(f"{RUN}/metrics/*.csv")):
    d = pd.read_csv(p)
    ringkas.append(dict(service=os.path.basename(p)[:-4], baris=len(d), kolom=d.shape[1] - 1,
                        nan=int(d.isna().sum().sum()), mulai=d.timestamp.min(), selesai=d.timestamp.max()))
ringkas = pd.DataFrame(ringkas)
print(ringkas[["baris", "kolom", "nan"]].agg(["min", "max"]))
print("Semua mulai di detik yang sama:", ringkas.mulai.nunique() == 1)
```

Metrics adalah modalitas yang paling "bersih": lengkap untuk 27 service, tiap detik, tanpa celah.

### Plot metrics dengan area fault

```python
run_id = os.path.basename(RUN)[3:20]
fr = faults[faults.run == run_id]
t0 = fr.run_start.iloc[0]

SERVICE = "ts-food-service"     # coba ganti dengan service lain di run ini: ts-travel-service, ts-contacts-service
m = pd.read_csv(f"{RUN}/metrics/{SERVICE}.csv")
fig, axes = plt.subplots(4, 1, figsize=(13, 8), sharex=True)
for ax, col in zip(axes, ["cpu_usage_total", "memory_usage", "rx_bytes", "tx_bytes"]):
    ax.plot((m.timestamp - t0) / 60, m[col], lw=0.6)
    ax.set_ylabel(col, fontsize=8)
    for _, f in fr.iterrows():
        kena = f.service == SERVICE
        ax.axvspan((f.start - t0) / 60, (f.start + f.durasi - t0) / 60,
                   color=warna[f.fault] if kena else "grey", alpha=0.25 if kena else 0.08)
axes[0].set_title(f"{SERVICE}: area berwarna = fault di service ini, abu-abu = fault di service lain")
axes[-1].set_xlabel("menit sejak run mulai")
plt.tight_layout(); plt.show()
```

**Yang perlu diamati:**

- Saat `cpu_load` di `ts-food-service` (oranye), `cpu_usage_total` melonjak jelas.
- Saat `network_delay` dan `network_loss`, CPU tidak berubah banyak. Petunjuknya ada di `rx_bytes`/`tx_bytes`, atau lebih jelas lagi di trace (A5 dan B2).
- Artinya, **tiap jenis fault paling terlihat di modalitas yang berbeda**. Inilah alasan memakai banyak modalitas, dan alasan kenapa cara menggabungkannya (fusion) penting.

**Tugas A3:** Ganti `SERVICE` dengan service yang **tidak** di-fault di run ini, misalnya `ts-order-service`. Apakah metriknya ikut berubah saat service lain di-fault?

---

## A4. Logs

```python
logs = json.load(open(f"{RUN}/logs.json"))
print("Tipe:", type(logs).__name__, "| jumlah kunci (service):", len(logs))
print("Total baris log:", sum(len(v) for v in logs.values()), "\n")
print(pd.Series({k: len(v) for k, v in logs.items()}).sort_values(ascending=False).to_string())
print("\nContoh baris:\n", logs["ts-auth-service"][0])
```

**Hasil yang diharapkan:**

- 27 kunci, tapi hanya **14 service yang punya log**. 13 service lainnya kosong sama sekali.
- Total 8.995 baris. `ts-travel-service` paling banyak (2.301).
- Format tiap baris adalah log Spring Boot:

```
2022-04-17 13:22:01.494  INFO 1 --- [io-12340-exec-3] auth.service.impl.TokenServiceImpl       : LOGIN USER :fdse_microservice __ 111111 __ AAAA
└─ waktu ────────────┘ └level┘ └pid┘ └─ thread ──────┘ └─ logger (class Java) ─────────────┘   └─ pesan
```

### Parsing log menjadi tabel

```python
pola = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s+(\w+)\s+\d+\s+---\s+\[(.*?)\]\s+(\S+)\s*:\s?(.*)$")
baris, gagal = [], 0
for service, lines in logs.items():
    for line in lines:
        cocok = pola.match(line)
        if cocok:
            baris.append((service,) + cocok.groups())
        else:
            gagal += 1
L = pd.DataFrame(baris, columns=["service", "waktu", "level", "thread", "logger", "pesan"])
L["ts"] = (pd.to_datetime(L.waktu) - pd.Timestamp("1970-01-01")).dt.total_seconds()
print("Baris gagal di-parse:", gagal)
print(L.level.value_counts(), "\n")
print(L.logger.value_counts().head(8))
```

**Hasil yang diharapkan:** tidak ada baris yang gagal di-parse. **Semua level-nya `INFO`**, tidak ada `ERROR` atau `WARN` sama sekali. Jadi, berbeda dengan dugaan awal, fault tidak bisa dideteksi dengan mencari kata "error". Yang berubah adalah **frekuensi** jenis-jenis pesan. Itu sebabnya EADRO mengubah log menjadi jumlah kemunculan tiap template per waktu, lalu memakai model Hawkes.

### Bukti selisih 8 jam

Baris log tidak menyimpan zona waktu. Kita bandingkan rentang waktunya dengan rentang run dari file label:

```python
run_start, run_end = fr.run_start.iloc[0], fr.run_end.iloc[0]
print("Tanpa koreksi : log mulai %+.0f s dari awal run, berakhir %+.0f s dari akhir run"
      % (L.ts.min() - run_start, L.ts.max() - run_end))
L["ts"] = L.ts - SHIFT
print("Koreksi -8 jam: log mulai %+.0f s dari awal run, berakhir %+.0f s dari akhir run"
      % (L.ts.min() - run_start, L.ts.max() - run_end))
```

**Hasil yang diharapkan:**

```
Tanpa koreksi : log mulai +28860 s dari awal run, ...     ← sekitar 8 jam di luar run
Koreksi -8 jam: log mulai +60 s dari awal run, berakhir -56 s dari akhir run   ← pas di dalam run
```

Log ditulis dengan jam lokal server (UTC+8, kemungkinan zona waktu Tiongkok), sedangkan label dan metrics memakai UTC.

### Template log

```python
# Template kasar: ganti ID panjang dan angka dengan placeholder
L["template"] = (L.pesan.str.replace(r"[0-9a-fA-F\-]{8,}", "<ID>", regex=True)
                        .str.replace(r"\d+", "<N>", regex=True))
print("Jumlah template unik:", L.template.nunique())
L.template.value_counts().head(8)
```

Hasilnya sekitar **169 template**. Yang paling sering adalah `Span reported: ...`, yaitu log dari library tracing Jaeger, bukan log bisnis. EADRO memakai parser Drain untuk membuat template yang lebih rapi. Versi kasar di atas cukup untuk mendapat gambaran.

**Tugas A4:** Sebutkan service yang pernah di-fault di run ini tetapi tidak punya log. Apa konsekuensinya untuk lokalisasi root cause di service itu?

---

## A5. Traces

### Struktur

```python
traces = json.load(open(f"{RUN}/spans.json"))
t = traces[0]
print("Jumlah trace:", len(traces))
print("Kunci satu trace :", list(t.keys()))
print("Kunci satu span  :", list(t["spans"][0].keys()))
print("Contoh processes :", {k: v["serviceName"] for k, v in list(t["processes"].items())[:3]})
```

Satu **trace** adalah satu request pengguna. Isinya:

- `spans`: langkah-langkah di dalam request. Setiap span adalah satu pemanggilan, dengan `startTime` (mikrodetik) dan `duration` (mikrodetik).
- `processes`: tabel `processID → serviceName`. Span hanya menyimpan `processID`, jadi nama service-nya harus dicari di sini.
- Di `tags` setiap span ada `span.kind`:
  - `client`: sisi **pemanggil**. Durasinya mencakup waktu jaringan menuju service tujuan.
  - `server`: sisi **yang dipanggil**. Durasinya hanya waktu proses di dalam service itu.
- Service tujuan untuk client span bisa dibaca dari host di `http.url`, misalnya `http://ts-verification-code-service:15678/...`.

### Meratakan span jadi tabel

```python
baris = []
for tr in traces:
    proc = {k: v["serviceName"] for k, v in tr["processes"].items()}
    for s in tr["spans"]:
        tags = {tg["key"]: tg["value"] for tg in s["tags"]}
        url = tags.get("http.url")
        baris.append(dict(traceID=s["traceID"], spanID=s["spanID"],
                          service=proc[s["processID"]], op=s["operationName"],
                          kind=tags.get("span.kind"), status=tags.get("http.status_code"),
                          callee=urlparse(url).hostname if url else None,
                          start=s["startTime"] / 1e6, dur_ms=s["duration"] / 1e3))
S = pd.DataFrame(baris)
unik = S.drop_duplicates(["traceID", "spanID"])
print("Baris span:", len(S), "| span unik:", len(unik), "| rasio duplikat: %.2f" % (len(S) / len(unik)))
S = unik.copy()
```

**Hasil yang diharapkan:** 18.346 baris, tapi hanya 4.588 span unik. **Setiap span muncul sekitar 4 kali.** Kalau tidak dibuang, jumlah request dan rata-rata latency jadi salah.

### Selisih waktu dan span basi

```python
S["t"] = S.start - SHIFT
S["di_run"] = S.t.between(run_start, run_end)
print("Porsi span di dalam rentang run: %.1f%%" % (100 * S.di_run.mean()))
print("Span paling awal: %.1f jam sebelum run mulai" % ((run_start - S.t.min()) / 3600))
S = S[S.di_run].copy()
print("Span yang dipakai:", len(S), "dari", S.traceID.nunique(), "trace")
```

Ada dua masalah di sini:

1. Waktu span juga bergeser +8 jam, sama seperti log.
2. Setelah dikoreksi pun, sekitar **22% span di run ini berada di luar rentang run**. Ada yang sampai 24 jam sebelumnya. Ini span "basi" yang ikut terekspor dari Jaeger. Di run lain porsinya antara 6% dan 47%. Span seperti ini harus dibuang.

### Siapa yang punya trace?

```python
print("Status HTTP:", S.status.value_counts().to_dict())
print("Jenis span :", S.kind.value_counts().to_dict(), "\n")

client = S[S.kind == "client"]
print("Service sebagai PEMANGGIL (client span):", client.service.nunique())
print("Service sebagai TUJUAN (callee dari http.url):", client.callee.nunique())
print(client.callee.value_counts().to_string())
```

**Hasil yang diharapkan:** 7 service pemanggil, dan **9 service tujuan** di run ini: `route`, `station`, `basic`, `ticketinfo`, `verification-code`, `security`, `order`, `order-other`, `contacts`.

**Yang perlu diamati:**

- **Semua status HTTP 200**, termasuk saat fault. Jadi fault tidak muncul sebagai error HTTP, melainkan sebagai latency yang membesar.
- Pipeline kita (`pipeline/build_traces.py`) memakai **client span**, dan mengaitkan latency-nya ke service **tujuan**. Alasannya, `network_delay` dan `network_loss` di service B baru terlihat dari sisi A yang memanggil B. Server span di B tidak menangkapnya.
- Kalau dihitung dari semua run, hanya **9 dari 27 service** yang pernah menjadi tujuan client span. Akibatnya, untuk 54 dari 81 fault, service yang menjadi root cause tidak punya data trace sama sekali (lihat `Report/Temuan_Data_dan_Sweep_T.md`).

### Trace datang berkelompok

```python
detik_ada = np.sort(np.floor(S.t).astype(int).unique())
print("Detik yang punya span: %d dari %d detik run" % (len(detik_ada), int(run_end - run_start)))
print("Jarak antar detik berisi span:", pd.Series(np.diff(detik_ada)).value_counts().head(5).to_dict())

fig, ax = plt.subplots(figsize=(13, 2.5))
per_detik = pd.Series(np.floor(S.t - run_start).astype(int)).value_counts().sort_index()
ax.vlines(per_detik.index / 60, 0, per_detik.values, lw=0.8)
ax.set_xlabel("menit sejak run mulai"); ax.set_ylabel("span/detik")
ax.set_title("Span hanya muncul sekitar sekali per menit")
plt.tight_layout(); plt.show()
```

**Hasil yang diharapkan:** hanya sekitar 236 dari 6.461 detik yang berisi span. Jarak paling umum antar detik berisi span adalah **60 detik** atau **1 detik**. Artinya, generator beban mengirim satu gelombang request sekitar sekali per menit, dan tiap gelombang berlangsung sekitar 1 sampai 4 detik.

**Tugas A5:** Kalau window EADRO panjangnya T = 10 detik, kira-kira berapa persen window yang berisi minimal satu span? Tulis tebakanmu dulu, lalu cek di B3.

---

# Bagian B. EDA Lintas Modalitas

## B1. Cakupan modalitas per service

```python
service_list = sorted(os.path.basename(p)[:-4] for p in glob.glob(f"{RUN}/metrics/*.csv"))
cakupan = pd.DataFrame(index=service_list)
cakupan["metrics"] = True
cakupan["logs"] = [len(logs.get(s, [])) > 0 for s in service_list]
cakupan["trace (callee)"] = cakupan.index.isin(client.callee.unique())
cakupan["di-fault di run ini"] = cakupan.index.isin(fr.service)
print(cakupan.sum().to_string(), "\n")
cakupan.sort_values(["trace (callee)", "logs"], ascending=False)
```

Tabel ini adalah **gambaran terpenting untuk studi fusion**. Hanya metrics yang lengkap untuk semua service. Log tersedia untuk sekitar separuh service, dan trace untuk lebih sedikit lagi. Bagi banyak service, dua dari tiga input fusion hanya berisi nol.

Konsekuensinya untuk fusion: mekanisme yang bisa **mengecilkan bobot modalitas yang kosong atau tidak informatif** punya peluang lebih baik. Ini cocok dengan temuan di Progress 6, yaitu GLU membantu pada fault baru, dan dengan motivasi KPI-aware attention di MULAN (F3).

---

## B2. Satu fault dilihat dari tiga modalitas

Kita pilih service yang punya ketiga modalitas dan di-fault di run ini, yaitu `ts-contacts-service`. (`ts-travel-service` juga di-fault, tapi di run ini tidak ada client span yang memanggilnya, jadi trace-nya kosong. Ini contoh nyata dari B1.)

Kita lihat `network_delay` mulai 10 menit sebelum fault sampai 10 menit sesudahnya. Rentang ini ikut mencakup fault tetangga di service yang sama. Area fault tetangga ikut diwarnai sesuai jenisnya.

```python
SERVICE, FAULT = "ts-contacts-service", "network_delay"    # coba juga FAULT = "cpu_load"
f1 = fr[(fr.service == SERVICE) & (fr.fault == FAULT)].iloc[0]
a, b = f1.start - 600, f1.start + f1.durasi + 600

mt = pd.read_csv(f"{RUN}/metrics/{SERVICE}.csv")
mt = mt[mt.timestamp.between(a, b)]
lg = L[(L.service == SERVICE) & L.ts.between(a, b)]
lg_per_menit = np.floor((lg.ts - f1.start) / 60).value_counts().sort_index()
tr = client[(client.callee == SERVICE) & client.t.between(a, b)]

fig, axes = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
axes[0].plot((mt.timestamp - f1.start) / 60, mt.cpu_usage_total, lw=0.7)
axes[0].set_ylabel("CPU total")
axes[1].bar(lg_per_menit.index + 0.5, lg_per_menit.values, width=0.9)
axes[1].set_ylabel("log / menit")
axes[2].scatter((tr.t - f1.start) / 60, tr.dur_ms, s=10)
axes[2].set_yscale("log"); axes[2].set_ylabel("latency panggilan\nke service (ms)")
for ax in axes:
    for _, f in fr[fr.service == SERVICE].iterrows():
        ax.axvspan((f.start - f1.start) / 60, (f.start + f.durasi - f1.start) / 60,
                   color=warna[f.fault], alpha=0.25 if f.fault == FAULT else 0.08)
    ax.set_xlim(-10, 20)
axes[-1].set_xlabel("menit relatif terhadap awal fault")
axes[0].set_title(f"{SERVICE}, {FAULT} (area tebal); fault tetangga diwarnai tipis")
plt.tight_layout(); plt.show()

sebelum = tr[tr.t < f1.start].dur_ms.median()
selama = tr[tr.t.between(f1.start, f1.start + f1.durasi)].dur_ms.median()
print(f"Median latency sebelum fault: {sebelum:.1f} ms | selama fault: {selama:.1f} ms | titik trace: {len(tr)}")
```

**Hasil yang diharapkan:** `Median latency sebelum fault: 2.8 ms | selama fault: 14311.2 ms`.

**Yang perlu diamati:**

- **Trace**: latency panggilan ke `ts-contacts-service` melonjak sekitar 5.000 kali lipat (dari milidetik ke belasan detik). Untuk `network_delay`, ini sinyal paling kuat.
- **Metrics**: CPU **tinggi sebelum** fault, karena 10 menit sebelumnya ada fault `cpu_load` di service yang sama (area oranye tipis). Begitu `cpu_load` selesai, CPU jatuh ke hampir nol dan datar. Jadi `network_delay` sendiri tidak terlihat di CPU.
- **Log**: sebelum fault, stabil 8 baris per menit. Selama fault, naik turun antara 0 dan 8 (request yang selesai jadi lebih sedikit). Sinyalnya ada, tapi lemah.
- **Jumlah titik trace**: dalam 30 menit hanya ada sekitar 20 titik. Banyak window pendek tidak akan menangkap lonjakan ini.

**Tugas B2:** Ubah `FAULT = "cpu_load"`, lalu jalankan ulang. Modalitas mana yang paling jelas sekarang? (Hasil uji: CPU rata-rata naik dari sekitar 0,1 menjadi sekitar 47, sedangkan latency tidak naik.) Kesimpulan apa yang bisa kamu tarik soal "modalitas mana yang penting" bila jenis fault-nya berbeda?

---

## B3. Peluang sebuah window berisi trace

```python
for T in [5, 10, 30, 60]:
    mulai = np.arange(int(run_start), int(run_end) - T)
    ada = np.isin(mulai[:, None] + np.arange(T), detik_ada).any(axis=1)
    print(f"T = {T:>2} detik: {100 * ada.mean():5.1f}% window berisi minimal satu span")
```

**Hasil yang diharapkan (run ini):** T=5 sekitar 15%, T=10 sekitar 25%, T=30 sekitar 56%, T=60 sekitar 97%.

Jika dihitung dari semua run dan hanya untuk service tujuan, angkanya lebih kecil lagi (18% untuk T=10, lihat `Report/Temuan_Data_dan_Sweep_T.md`). Inilah alasan kita mencoba T=30 di Progress 6.

---

## B4. Dari data mentah ke sampel EADRO

EADRO tidak membaca data per detik secara langsung. Data dipotong menjadi **window** sepanjang T detik yang digeser per 1 detik. Setiap window menjadi satu sampel:

- **Input**: untuk tiap service, ada metrics T×7, jumlah log per template, dan latency trace selama T detik.
- **Label deteksi**: 1 kalau window tumpang tindih dengan fault, 0 kalau tidak.
- **Label lokalisasi**: indeks service yang di-fault (−1 untuk window normal).

```python
T = 10
mulai = np.arange(int(run_start), int(run_end) - T)
label = np.zeros(len(mulai), dtype=int)
culprit = np.full(len(mulai), -1)
for _, f in fr.iterrows():
    kena = (mulai + T > f.start) & (mulai < f.start + f.durasi)
    label[kena] = 1
    culprit[kena] = service_list.index(f.service)
print(f"Jumlah window: {len(mulai)} | anomali: {label.mean():.1%} | normal: {1 - label.mean():.1%}")
print("Window per service biang:", pd.Series(culprit[culprit >= 0]).map(lambda i: service_list[i]).value_counts().to_dict())
```

**Hasil yang diharapkan:** sekitar 6.451 window, **85% anomali**, dan hanya 15% normal. Window normal hanya datang dari celah sekitar 2 menit di antara fault. Karena itu 3 run tanpa fault penting: tanpa run tersebut, model hampir tidak pernah melihat kondisi normal.

Window yang berdampingan berbagi T−1 detik data. Dengan T=10, dua window bertetangga sama 9 dari 10 detiknya. Inilah sumber kebocoran kalau window diacak sebelum dibagi ke train dan test, seperti di kode rilis EADRO.

---

## B5. (Opsional) Membandingkan semua run

```python
ringkas_run = []
for r in fault_runs + nofault_runs:
    lg = json.load(open(f"{r}/logs.json"))
    ringkas_run.append(dict(run=os.path.basename(r)[3:20],
                            jenis="fault" if r in fault_runs else "normal",
                            service_berlog=sum(1 for v in lg.values() if v),
                            baris_log=sum(len(v) for v in lg.values()),
                            file_metrics=len(os.listdir(f"{r}/metrics")),
                            spans_MB=round(os.path.getsize(f"{r}/spans.json") / 1e6, 1)))
pd.DataFrame(ringkas_run)
```

**Yang perlu diamati:**

- Setiap run punya 27 file metrics, dan 13 sampai 15 service berlog.
- Run normal lebih panjang (sekitar 2,25 jam) dan log-nya lebih banyak.
- Ketiga run normal punya **jumlah baris log yang persis sama** (13.668), meskipun isi filenya berbeda (checksum berbeda). Kemungkinan generator beban berjalan dengan skrip yang sama persis dan tidak ada gangguan yang mengubah alurnya.

---

## Ringkasan temuan

| # | Temuan | Dampak di pipeline |
|---|---|---|
| 1 | 12 run: 9 berfault (81 fault) + 3 normal | Paper menyebut 162 fault; data publik hanya separuhnya |
| 2 | 27 service × 3 jenis fault, masing-masing tepat sekali, 600 detik | Split `leave_event_out` menyisihkan satu jenis fault per service |
| 3 | Metrics lengkap: 27 service, 7 kolom, tiap 1 detik, tanpa NaN | Modalitas paling andal |
| 4 | Log hanya di 13 sampai 15 service; semuanya level INFO | Sinyal ada di frekuensi template, bukan kata "error" |
| 5 | Waktu log dan span = UTC + 8 jam | Dikoreksi di `pipeline/common.py` (`SPAN_TZ_SHIFT_S`) |
| 6 | Setiap span muncul sekitar 4 kali | Dideduplikasi berdasarkan `(traceID, spanID)` |
| 7 | 6 sampai 47% span berada di luar rentang run | Dibuang (`dlmRun` di `build_traces.py`) |
| 8 | Semua HTTP 200; fault terlihat sebagai latency | Pakai latency client span ke service tujuan |
| 9 | Trace datang sekitar sekali per menit; hanya 9 service yang punya trace sebagai tujuan | Banyak window tanpa trace; alasan mencoba T=30 |
| 10 | 85% window di run berfault adalah anomali | Run normal dibutuhkan untuk menyeimbangkan |
| 11 | Window bertetangga berbagi T−1 detik | Split acak bocor; pakai `within_event` / `leave_event_out` |

---

## Pertanyaan refleksi

1. Fault jenis apa yang paling mudah dideteksi dari metrics saja? Fault jenis apa yang paling butuh trace?
2. Kalau sebuah service tidak punya log dan trace, informasi apa yang tersisa untuk melokalisasinya? Apakah fusion masih ada gunanya untuk service itu?
3. Fusion F1 (concat → FC → GLU) menerima vektor nol untuk modalitas yang kosong. Bagaimana menurutmu GLU memperlakukan vektor nol tersebut dibandingkan ReLU (F2)?
4. **Persiapan F3 (MULAN, KPI-aware attention).** MULAN butuh satu deret waktu KPI sebagai acuan. Dari eksplorasi ini, kandidat mana yang paling masuk akal, dan apa kelemahannya?
   - Latency client span (berdasarkan B2 dan B3: kuat, tapi jarang).
   - `cpu_usage_total` rata-rata semua service (rapat, tapi tidak peka terhadap fault jaringan).
   - Jumlah log per detik (rapat, tapi hanya separuh service yang punya log).
5. Dengan 85% window berlabel anomali, berapa F1-score yang didapat model yang selalu menjawab "anomali" di run berfault? Apa artinya bagi cara kita membaca F1-score deteksi?
