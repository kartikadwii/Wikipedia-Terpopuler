# Pemantau Wikipedia Terpopuler: Rencana Implementasi

> **Untuk pelaksana (agentic workers):** WAJIB pakai superpowers:subagent-driven-development (disarankan) atau superpowers:executing-plans untuk mengerjakan rencana ini task demi task. Langkah memakai kotak centang (`- [ ]`).

**Goal:** Sistem otomatis yang mengambil 50 artikel teratas id.wikipedia tiap 2–3 hari, mengabari lewat Telegram, dan menampilkannya di dashboard, tanpa laptop menyala.

**Architecture:** Workflow GitHub Actions harian menjalankan `run_scrape.py`. Skrip memeriksa jatuh tempo, mengambil top 50 untuk tiap tanggal yang belum ada, menambahkannya ke CSV, mengirim ringkasan ke Telegram, lalu workflow meng-commit CSV. Dashboard Streamlit membaca CSV yang sama.

**Tech Stack:** Python 3.11+, requests, pandas, streamlit, pytest, GitHub Actions.

**Spec:** `docs/spec.md` (Bagian 1 dokumen asli).

## Global Constraints

- Jumlah artikel per hari: 50 (setelah halaman non-artikel disaring).
- Interval: `INTERVAL_HARI` bawaan 3, nilai yang dimaksud 2 atau 3; nilai kurang dari 1 ditolak.
- Proyek Wikimedia: id.wikipedia; semua tanggal dalam UTC.
- Setiap permintaan ke Wikimedia membawa User-Agent deskriptif dengan kontak; jeda 0,5 detik antar permintaan, retry 3 kali dengan backoff untuk 429 dan 5xx.
- Pesan Telegram maksimal 4000 karakter.
- `BOT_TOKEN` dan `CHAT_ID` hanya dari environment atau GitHub Secrets; tidak pernah ditulis ke file yang di-commit atau ke pesan galat.
- CSV berkode UTF-8.
- Semua tes berjalan tanpa internet.

## Review Focus

1. Putaran pertama dengan CSV kosong: mengambil `INTERVAL_HARI` hari terakhir dan ringkasan menyebut "data awal", bukan 50 artikel "baru". Tes di Task 1 dan Task 3.
2. Jeda panjang (jadwal terlewat berminggu-minggu): hanya 7 hari terbaru diambil, tidak ada ratusan permintaan. Tes di Task 1.
3. Satu tanggal belum tersedia (404): dilewati, putaran lain tetap sukses, dan tercatat di pesan. Tes di Task 2 dan Task 5.
4. Notifikasi gagal: data tetap tersimpan dan workflow tetap meng-commit. Tes di Task 5.
5. Judul artikel berkarakter khusus (koma, tanda kutip, huruf beraksen): utuh setelah disimpan dan dibaca ulang dari CSV. Tes di Task 1.

## Struktur file

| File | Tanggung jawab |
|---|---|
| `config.py` | Membaca pengaturan dari environment |
| `wiki_client.py` | Mengambil dan menyaring top artikel satu hari |
| `storage.py` | Membaca dan menulis CSV, penentuan tanggal yang perlu diambil dan jatuh tempo |
| `analysis.py` | Pengelompokan pergerakan peringkat, ringkasan putaran, tabel dan tren untuk dashboard |
| `notifier.py` | Menyusun dan mengirim pesan Telegram |
| `run_scrape.py` | Orkestrasi satu putaran |
| `dashboard/app.py` | Dashboard Streamlit |
| `.github/workflows/scrape.yml` | Jadwal otomatis |
| `data/top_artikel.csv` | Data (kolom `tanggal`, `peringkat`, `artikel`, `jumlah_baca`, `diambil_pada`) |
| `tests/` | Tes untuk setiap modul |

Catatan: tes ditulis sebagai nama dan asersi dalam kalimat, bukan kode.

## Task 1: Pengaturan dan penyimpanan

**Files:** Create `config.py`, `storage.py`, `requirements.txt`, `.gitignore`, `.env.example`, `tests/test_config.py`, `tests/test_storage.py`.

**Interfaces:**

Produces: `Pengaturan` (dataclass: `bot_token: str`, `chat_id: str`, `interval_hari: int = 3`, `jumlah_teratas: int = 50`, `maks_hari_susul: int = 7`, `proyek: str = "id.wikipedia"`, `user_agent: str`, `dashboard_url: str`, `data_dir: Path`); `ambil_pengaturan() -> Pengaturan`; `KOLOM: list[str]`; `muat(path: Path) -> DataFrame`; `tambah(path: Path, baris: DataFrame) -> int` (jumlah baris baru); `tanggal_terakhir(df: DataFrame) -> date | None`; `waktu_run_terakhir(df: DataFrame) -> date | None`; `sudah_jatuh_tempo(run_terakhir: date | None, hari_ini: date, interval_hari: int) -> bool`; `tanggal_yang_perlu_diambil(terakhir: date | None, hari_ini: date, interval_hari: int, maks_hari: int) -> list[date]`.

- [ ] **Step 1: Tulis tes yang gagal**
  - `test_ambil_pengaturan_bawaan`: dengan `BOT_TOKEN` dan `CHAT_ID` saja, `jumlah_teratas == 50` dan `interval_hari == 3`.
  - `test_ambil_pengaturan_menolak_interval_nol_dan_token_kosong`: `INTERVAL_HARI=0` atau `BOT_TOKEN` hilang memicu `ValueError`.
  - `test_muat_file_belum_ada`: hasil kosong dengan `list(df.columns) == KOLOM`.
  - `test_tambah_tidak_menggandakan`: menambah 2 baris mengembalikan 2; menambah baris yang sama mengembalikan 0 dan file tetap 2 baris (kunci: `tanggal` + `artikel`).
  - `test_judul_karakter_khusus_utuh`: judul `Soekarno, "Bung" Karno — Édith` sama persis setelah `tambah` lalu `muat`.
  - `test_tanggal_pertama_kali`: `terakhir=None`, `hari_ini=2026-11-15`, `interval_hari=3` menghasilkan 12, 13, 14 November 2026.
  - `test_tanggal_lanjut_setelah_terakhir`: `terakhir=2026-11-11` menghasilkan 12, 13, 14 November; `terakhir=2026-11-14` menghasilkan daftar kosong.
  - `test_tanggal_dibatasi_maks_hari`: `terakhir=2026-11-01`, `maks_hari=7` menghasilkan 8 sampai 14 November.
  - `test_jatuh_tempo`: `None` benar; run terakhir 12 November dan `hari_ini` 15 November dengan interval 3 benar; `hari_ini` 14 November salah; interval 2 pada 14 November benar.
- [ ] **Step 2:** Jalankan `pytest tests/test_config.py tests/test_storage.py -v`. Harapan: gagal karena modul belum ada.
- [ ] **Step 3:** Implementasikan semua antarmuka di atas. Penyimpanan memakai pandas, kolom `tanggal` bertipe tanggal, `peringkat` dan `jumlah_baca` bertipe bilangan bulat, tulis dengan UTF-8. `tanggal_yang_perlu_diambil` tidak pernah mengembalikan tanggal hari ini atau sesudahnya.
- [ ] **Step 4:** Jalankan perintah yang sama. Harapan: semua lulus.
- [ ] **Step 5:** `git add . && git commit -m "feat: pengaturan dan penyimpanan CSV"`

## Task 2: Klien Wikimedia

**Files:** Create `wiki_client.py`, `tests/test_wiki_client.py`.

**Interfaces:**

Consumes: `Pengaturan` (hanya `proyek`, `user_agent`, `jumlah_teratas`).

Produces: `ArtikelBaca` (dataclass: `peringkat: int`, `artikel: str`, `jumlah_baca: int`); `ambil_top_artikel(tanggal: date, proyek: str, user_agent: str, jumlah: int = 50, sesi=None, jeda: float = 0.5) -> list[ArtikelBaca] | None` (`None` bila data tanggal itu belum tersedia).

- [ ] **Step 1: Tulis tes yang gagal (sesi palsu, tanpa internet)**
  - `test_parse_saring_dan_nomori_ulang`: daftar berisi `Halaman_Utama`, `Istimewa:Pencarian`, lalu artikel biasa; hasil tidak memuat dua yang pertama, garis bawah menjadi spasi, peringkat dinomori ulang mulai 1.
  - `test_dibatasi_jumlah`: daftar 200 artikel dengan `jumlah=50` menghasilkan tepat 50.
  - `test_kurang_dari_jumlah_tidak_error`: daftar 10 artikel menghasilkan 10.
  - `test_404_mengembalikan_none`.
  - `test_retry_429_lalu_berhasil`: respons 429 lalu 200 menghasilkan data (jeda diganti agar tes cepat).
  - `test_user_agent_dikirim`: header `User-Agent` sama dengan argumen.
- [ ] **Step 2:** Jalankan `pytest tests/test_wiki_client.py -v`. Harapan: gagal.
- [ ] **Step 3:** Implementasikan `ambil_top_artikel` memakai endpoint top pageviews per proyek per hari (`https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{proyek}/all-access/{YYYY}/{MM}/{DD}`). Saring judul yang mengandung `:` dan `Halaman_Utama` sebelum memotong ke `jumlah`.
- [ ] **Step 4:** Jalankan perintah yang sama. Harapan: lulus.
- [ ] **Step 5:** `git add . && git commit -m "feat: klien pageviews Wikimedia"`

## Task 3: Analisis pergerakan peringkat

**Files:** Create `analysis.py`, `tests/test_analysis.py`.

**Interfaces:**

Produces: `KELOMPOK = ("baru", "naik", "turun", "bertahan")`; `klasifikasi_pergerakan(sekarang: DataFrame, sebelumnya: DataFrame) -> DataFrame` (kolom `artikel`, `peringkat`, `peringkat_sebelum`, `selisih`, `kelompok`; `selisih = peringkat_sebelum - peringkat`, positif berarti naik); `Ringkasan` (dataclass: `tanggal_awal: date`, `tanggal_akhir: date`, `jumlah_baris: int`, `data_awal: bool`, `baru: list[str]`, `naik_tertinggi: list[tuple[str, int, int]]`, `teratas: tuple[str, int]`); `ringkas_putaran(baris_baru: DataFrame, semua: DataFrame) -> Ringkasan` (`baru` maksimal 5, `naik_tertinggi` maksimal 3 berisi artikel, dari, ke); `tabel_harian(semua: DataFrame, tanggal: date) -> DataFrame`; `tren_artikel(semua: DataFrame, artikel: list[str]) -> DataFrame` (indeks tanggal, kolom per artikel, nilai `jumlah_baca`).

- [ ] **Step 1: Tulis tes yang gagal**
  - `test_klasifikasi_empat_kelompok`: artikel A peringkat 5 menjadi 2 (naik, selisih 3), B 2 menjadi 4 (turun, selisih -2), C 3 menjadi 3 (bertahan), D tidak ada kemarin (baru, `peringkat_sebelum` kosong).
  - `test_sebelumnya_kosong_semua_baru`.
  - `test_ringkas_putaran_data_awal`: bila semua hanya punya satu tanggal, `data_awal` benar dan `baru == []`.
  - `test_ringkas_putaran_isi`: `baru` dan `naik_tertinggi` sesuai contoh dan tidak melebihi batas.
  - `test_tabel_harian_memakai_tanggal_sebelumnya_yang_tersedia`: tanggal 14 dibandingkan dengan 12 bila 13 tidak ada.
  - `test_tren_artikel_judul_tidak_ada`: kolom kosong, tidak error.
- [ ] **Step 2:** Jalankan `pytest tests/test_analysis.py -v`. Harapan: gagal.
- [ ] **Step 3:** Implementasikan semua antarmuka; `Int64` pandas untuk kolom yang bisa kosong.
- [ ] **Step 4:** Jalankan perintah yang sama. Harapan: lulus.
- [ ] **Step 5:** `git add . && git commit -m "feat: analisis pergerakan peringkat"`

## Task 4: Notifikasi Telegram

**Files:** Create `notifier.py`, `tests/test_notifier.py`.

**Interfaces:**

Consumes: `Ringkasan` dari Task 3.

Produces: `NotifikasiGagal(Exception)`; `susun_pesan(ringkasan: Ringkasan, dashboard_url: str, tanggal_dilewati: list[date] = []) -> str`; `susun_pesan_gagal(alasan: str) -> str`; `kirim_pesan(teks: str, token: str, chat_id: str, sesi=None) -> None`.

- [ ] **Step 1: Tulis tes yang gagal**
  - `test_pesan_memuat_rentang_tanggal_jumlah_baris_dan_url`.
  - `test_pesan_data_awal_tidak_menyebut_baru_masuk`.
  - `test_pesan_menyebut_tanggal_dilewati`.
  - `test_pesan_maksimal_4000_karakter`: 50 judul sangat panjang tetap 4000 karakter atau kurang.
  - `test_kirim_pesan_memanggil_sendMessage`: URL berakhir `sendMessage`, isi memuat `chat_id` dan `text` (sesi palsu).
  - `test_kirim_pesan_gagal_melempar_dan_tidak_membocorkan_token`: respons tidak ok melempar `NotifikasiGagal` dan teks galat tidak memuat token.
- [ ] **Step 2:** Jalankan `pytest tests/test_notifier.py -v`. Harapan: gagal.
- [ ] **Step 3:** Implementasikan memakai `requests` ke `https://api.telegram.org/bot<token>/sendMessage`; potong teks bila melebihi batas.
- [ ] **Step 4:** Jalankan perintah yang sama. Harapan: lulus.
- [ ] **Step 5:** `git add . && git commit -m "feat: notifikasi Telegram"`

## Task 5: Orkestrasi satu putaran

**Files:** Create `run_scrape.py`, `tests/test_run_scrape.py`.

**Interfaces:**

Consumes: semua antarmuka Task 1–4.

Produces: `jalankan(hari_ini: date, pengaturan: Pengaturan, klien=ambil_top_artikel, kirim=kirim_pesan, paksa: bool = False) -> int` (kode keluar 0 atau 1); `main() -> None` (membaca environment, opsi `--paksa`).

- [ ] **Step 1: Tulis tes yang gagal (klien dan pengirim palsu, folder data sementara)**
  - `test_belum_jatuh_tempo_keluar_0_tanpa_memanggil_klien`.
  - `test_putaran_normal`: tiga tanggal masing-masing 50 artikel menghasilkan CSV 150 baris, `kirim` dipanggil sekali, kode 0.
  - `test_tanggal_404_dilewati`: satu tanggal `None` menghasilkan 100 baris, kode 0, pesan menyebut tanggal itu.
  - `test_semua_tanggal_gagal`: kode 1, CSV tidak berubah, `kirim` dipanggil sekali dengan pesan gagal.
  - `test_notifikasi_gagal_data_tetap_tersimpan`: `kirim` melempar `NotifikasiGagal`, CSV tetap berisi data baru, kode 0.
  - `test_diulang_dengan_paksa_tidak_menggandakan_data`.
- [ ] **Step 2:** Jalankan `pytest tests/test_run_scrape.py -v`. Harapan: gagal.
- [ ] **Step 3:** Implementasikan alur: periksa jatuh tempo (kecuali `paksa`), tentukan tanggal, ambil per tanggal, tambah ke CSV, ringkas, kirim notifikasi di dalam `try/except NotifikasiGagal` (hanya dicatat sebagai peringatan).
- [ ] **Step 4:** Jalankan `pytest -v`. Harapan: seluruh tes Task 1–5 lulus.
- [ ] **Step 5:** `git add . && git commit -m "feat: orkestrasi putaran scraping"`

## Task 6: Workflow GitHub Actions

**Files:** Create `.github/workflows/scrape.yml`.

- [ ] **Step 1:** Buat repositori GitHub dan dorong kode; tambahkan Secrets `BOT_TOKEN` dan `CHAT_ID`, serta variabel `INTERVAL_HARI` dan `DASHBOARD_URL`.
- [ ] **Step 2:** Tulis workflow dengan: pemicu `schedule` harian pukul 03:17 UTC (bukan menit 00, karena awal jam padat) dan `workflow_dispatch`; `permissions: contents: write`; `concurrency` satu grup agar tidak ada dua putaran bersamaan; langkah checkout, setup Python, `pip install -r requirements.txt`, `python run_scrape.py`, lalu commit dan push `data/top_artikel.csv` hanya bila berubah (`git pull --rebase` sebelum push).
- [ ] **Step 3:** Jalankan manual lewat tab Actions (Run workflow) dengan opsi paksa. Harapan: putaran hijau, commit baru berisi data, pesan Telegram masuk.
- [ ] **Step 4:** Jalankan manual sekali lagi tanpa paksa. Harapan: putaran hijau, tidak ada commit baru (belum jatuh tempo).
- [ ] **Step 5:** Commit perubahan terakhir bila ada.

## Task 7: Dashboard

**Files:** Create `dashboard/app.py`, `tests/test_dashboard.py`.

**Interfaces:**

Consumes: `muat`, `tabel_harian`, `tren_artikel`, `KELOMPOK`.

Produces: halaman Streamlit dengan tiga metrik (total baris, hari tercakup, artikel unik), filter tanggal dan kelompok, grafik tren artikel terpilih, tabel, dan tombol unduh CSV.

- [ ] **Step 1: Tulis tes yang gagal**
  - `test_data_kosong_menampilkan_info`: dengan `streamlit.testing.v1.AppTest` dan CSV kosong, ada elemen info "Belum ada data" dan tidak ada error.
  - `test_data_ada_menampilkan_tiga_metrik`: dengan CSV contoh, ada tiga metrik bernilai sesuai contoh.
- [ ] **Step 2:** Jalankan `pytest tests/test_dashboard.py -v`. Harapan: gagal.
- [ ] **Step 3:** Implementasikan halaman; pembacaan data di-cache dengan waktu hidup pendek.
- [ ] **Step 4:** Jalankan perintah yang sama, lalu `streamlit run dashboard/app.py` dan periksa tampilan.
- [ ] **Step 5:** `git add . && git commit -m "feat: dashboard Streamlit"`

## Task 8: Deploy dan dokumentasi

**Files:** Create `README.md`.

- [ ] **Step 1:** Deploy `dashboard/app.py` ke Streamlit Community Cloud dari repositori yang sama dan catat URL-nya.
- [ ] **Step 2:** Isi variabel `DASHBOARD_URL` di GitHub dengan URL itu, lalu jalankan workflow manual dengan opsi paksa. Harapan: pesan Telegram memuat tautan dashboard dan dashboard menampilkan data baru.
- [ ] **Step 3:** Tulis README: cara kerja, cara mengisi Secrets, batas yang diketahui (jadwal bisa tertunda, dinonaktifkan setelah 60 hari tanpa aktivitas, dashboard tidur setelah 12 jam, jumlah baca bukan orang unik), etika pengambilan data, dan pernyataan penggunaan AI.
- [ ] **Step 4:** Commit: `git add README.md && git commit -m "docs: README"`

## Task 9: Perintah interaktif bot (hanya bila dosen mewajibkan; jika tidak, lewati)

**Files:** Create `api/telegram.py`, `tests/test_telegram_webhook.py`.

**Interfaces:**

Produces: `tangani_update(update: dict, baca_data=muat, picu_workflow=...) -> str` (teks balasan) untuk perintah `/terpopuler` (5 teratas hari terakhir), `/baru` (kelompok baru masuk) dan `/ambil` (memicu `workflow_dispatch` GitHub).

- [ ] **Step 1:** Tulis tes yang gagal: `test_terpopuler_membalas_lima_teratas`, `test_perintah_tidak_dikenal_membalas_bantuan`, `test_ambil_memicu_workflow_sekali`.
- [ ] **Step 2:** Jalankan `pytest tests/test_telegram_webhook.py -v`. Harapan: gagal.
- [ ] **Step 3:** Implementasikan fungsi dan pasang sebagai webhook pada layanan serverless pilihanmu.
- [ ] **Step 4:** Jalankan perintah yang sama. Harapan: lulus.
- [ ] **Step 5:** `git add . && git commit -m "feat: perintah interaktif bot"`
