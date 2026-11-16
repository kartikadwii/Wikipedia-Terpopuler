# Pemantau Wikipedia Terpopuler

Alat kecil yang mengambil 50 artikel Wikipedia bahasa Indonesia (`id.wikipedia`) terpopuler per tanggal, menyimpannya ke CSV, mengirim ringkasan ke Telegram, dan menampilkannya di dasbor Streamlit.

## Cara kerja

1. GitHub Actions menjalankan `run_scrape.py` setiap hari pukul 03:17 UTC (`.github/workflows/scrape.yml`).
2. Skrip memeriksa apakah sudah jatuh tempo: selisih hari sejak data terakhir diambil minimal `INTERVAL_HARI` (bawaan 3). Bila belum, skrip selesai tanpa melakukan apa pun dan tanpa pesan Telegram.
3. Bila jatuh tempo, skrip mengambil 50 artikel teratas untuk setiap tanggal yang belum ada, paling banyak 7 hari ke belakang (susul). Pada data kosong, yang diambil adalah `INTERVAL_HARI` hari terakhir.
4. Hasil ditambahkan ke `data/top_artikel.csv` (kolom `tanggal, peringkat, artikel, jumlah_baca, diambil_pada`).
5. Ringkasan dikirim ke Telegram, lalu workflow men-commit CSV bila berubah.
6. Dasbor Streamlit (`dashboard/app.py`) membaca CSV tersebut dari repositori.

Judul `Halaman_Utama`, `-`, dan judul yang memuat `:` (mis. `Istimewa:...`, `Wikipedia:...`) disaring, sehingga daftar hanya berisi artikel.

Bila tidak ada tanggal yang perlu diambil (data sudah mutakhir, termasuk pada run paksa yang diulang), run selesai dengan sukses dan tidak mengirim pesan Telegram.

## Variabel konfigurasi

| Nama | Jenis di GitHub | Wajib | Bawaan / keterangan |
|---|---|---|---|
| `BOT_TOKEN` | Secret | ya | Token bot Telegram |
| `CHAT_ID` | Secret | ya | ID chat tujuan pesan |
| `INTERVAL_HARI` | Variable | tidak | 3; bilangan bulat minimal 1 |
| `DASHBOARD_URL` | Variable | tidak | Kosong; bila diisi, tautan dimuat di pesan |
| `USER_AGENT` | env (lokal) | tidak | Dibentuk dari `GITHUB_REPOSITORY` |
| `DATA_DIR` | env (lokal) | tidak | `data` |

Nilai yang dikosongkan dianggap memakai bawaan. Workflow hanya meneruskan `BOT_TOKEN`, `CHAT_ID`, `INTERVAL_HARI`, dan `DASHBOARD_URL`; `USER_AGENT` tidak diteruskan, jadi di GitHub Actions User-Agent otomatis berbentuk `PemantauWikipediaTerpopuler/1.0 (+https://github.com/OWNER/REPO; tugas kuliah)`. Jangan memasukkan email pribadi ke User-Agent kecuali Anda sendiri memilih begitu.

## Langkah manual: deploy (belum dijalankan/diverifikasi)

Langkah berikut harus dikerjakan sendiri di akun GitHub, Telegram, dan Streamlit; semuanya belum dijalankan atau diverifikasi di lingkungan pengembangan.

### A. Buat bot Telegram dan cari chat id

1. Di Telegram, buka `@BotFather`, kirim `/newbot`, ikuti petunjuk, lalu salin token yang diberikan (bentuknya `123456:ABC...`). Simpan rahasia.
2. Buka bot Anda dan kirim pesan apa saja (mis. `/start`) agar ada percakapan.
3. Buka `https://api.telegram.org/bot<TOKEN>/getUpdates` di peramban (ganti `<TOKEN>`), lalu cari `"chat":{"id":...}`. Angka itu adalah `CHAT_ID`. Jangan membagikan URL ini karena memuat token.

### B. Buat repositori dan dorong kode

1. Buat repositori baru di GitHub (kosong, tanpa README).
2. Di folder proyek: `git remote add origin https://github.com/<akun>/<repo>.git`, lalu `git push -u origin <nama-branch>`. Pastikan kode ada di branch bawaan repositori (mis. `main`) agar jadwal harian berjalan, karena jadwal hanya berlaku pada branch bawaan.
3. Di repositori: Settings > Secrets and variables > Actions.
   - Tab Secrets: tambah `BOT_TOKEN` dan `CHAT_ID`.
   - Tab Variables: tambah `INTERVAL_HARI` (mis. `3`) dan, nanti, `DASHBOARD_URL`.
4. Pastikan Settings > Actions > General mengizinkan workflow (workflow sudah meminta `contents: write` untuk commit data).

### C. Deploy dasbor

1. Buka `share.streamlit.io`, masuk dengan GitHub, pilih New app.
2. Pilih repositori ini, branch bawaan, dan main file path `dashboard/app.py`. Deploy.
3. Salin URL aplikasi (mis. `https://<nama>.streamlit.app`).
4. Kembali ke GitHub, isi Variable `DASHBOARD_URL` dengan URL itu.

### D. Jalankan workflow dan periksa

1. Tab Actions > "Scrape top artikel Wikipedia" > Run workflow, centang `paksa`, jalankan.
2. Hasil yang diharapkan pada data kosong: run mengambil `INTERVAL_HARI` hari terakhir, commit `data: perbarui top artikel [skip ci]` muncul berisi `data/top_artikel.csv`, pesan Telegram masuk memuat "Ini data awal" dan tautan dasbor, dan dasbor menampilkan data setelah dimuat ulang (cache data dasbor 5 menit, dan Streamlit Cloud perlu menarik commit baru).
3. Jalankan lagi tanpa `paksa`. Hasil yang diharapkan: tidak ada commit baru dan tidak ada pesan (belum jatuh tempo).
4. Catatan: bila data sudah mutakhir, run paksa berikutnya juga tidak menghasilkan pesan. Pemeriksaan deploy yang menghasilkan pesan hanya run paksa pertama pada data kosong.

## Menjalankan secara lokal

```bash
pip install -r requirements.txt
python -m pytest                      # tes berjalan offline (tanpa jaringan)
export BOT_TOKEN=... CHAT_ID=...      # nilai Anda sendiri
python run_scrape.py                  # tambahkan --paksa untuk melewati pemeriksaan jatuh tempo
streamlit run dashboard/app.py
```

`USER_AGENT`, `INTERVAL_HARI`, `DASHBOARD_URL`, dan `DATA_DIR` bisa diatur juga lewat variabel lingkungan; contohnya di `.env.example`. Tes dasbor (`tests/test_dashboard.py`) dilewati otomatis bila `streamlit` tidak terpasang.

Catatan jujur: dasbor belum pernah dijalankan dengan Streamlit asli di lingkungan pengembangan. Ia hanya diverifikasi dengan harness palsu, dan tes AppTest akan berjalan bila streamlit terpasang. Perlu dicek saat deploy pertama.

## Batas yang diketahui

- Jadwal GitHub Actions bisa tertunda atau terlewat.
- Workflow terjadwal dinonaktifkan GitHub setelah 60 hari repositori tanpa aktivitas; aktifkan kembali secara manual di tab Actions.
- Dasbor Streamlit Community Cloud tidur setelah 12 jam tanpa pengunjung; bangunkan dengan satu klik sebelum presentasi.
- Jumlah baca adalah jumlah permintaan halaman, bukan orang unik.
- Tanggal yang gagal atau belum tersedia (404) dilewati dan tidak otomatis diulang bila tanggal sesudahnya berhasil; tanggal itu dicatat di pesan Telegram ("Tanggal dilewati"). Bila semua tanggal gagal, run keluar dengan kode 1 dan mengirim pesan gagal.
- Bot tidak interaktif: perintah seperti `/terpopuler` dan `/ambil` di luar cakupan. Bot hanya mengirim pesan.
- Kegagalan mengirim Telegram tidak menggagalkan run; data tetap tersimpan.

## Etika pengambilan data

- Sumber: API publik Wikimedia Pageviews (`wikimedia.org/api/rest_v1/metrics/pageviews/top`).
- User-Agent deskriptif yang menyebut proyek dan alamat repositori sebagai kontak.
- Jeda 0,5 detik sebelum tiap permintaan, dan 3 percobaan dengan backoff untuk status 429/5xx.
- Hanya satu permintaan kecil per tanggal (maksimal 7 per run).
- Hormati kebijakan penggunaan API Wikimedia.
- Data berupa statistik agregat judul artikel, bukan data pribadi.

## Pernyataan penggunaan AI

Proyek ini dikerjakan dengan bantuan Claude, asisten AI. Kode ditinjau dan diuji; manusia yang menjalankan proyek ini bertanggung jawab atas isi dan penggunaannya.
