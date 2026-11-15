# Pemantau Wikipedia Terpopuler: Rancangan (spec)

Proyek Pekan 12 · 15 November 2026

## Tujuan dan alasan

Tugas dosen: mengambil data dari web memakai kode, otomatis dan terjadwal, hasilnya diberitahukan lewat bot Telegram dan seluruh data tampil di dashboard beserta pengelompokannya. Topik yang dipilih: artikel Wikipedia Indonesia yang paling banyak dibaca. Syarat baru: sistem tidak boleh bergantung pada laptop yang menyala.

## Keputusan dari pengguna

- Data: 50 artikel teratas per hari.
- Pengambilan 2 atau 3 hari sekali, bukan setiap hari.
- Berjalan otomatis tanpa laptop, lalu mengirim notifikasi ke bot Telegram dan menambah data ke dashboard.

## Keputusan perancang (dapat dikoreksi)

- Edisi id.wikipedia lewat Pageviews API Wikimedia (publik, tanpa kunci, wajib User-Agent deskriptif dengan kontak).
- Penjadwal: GitHub Actions yang berjalan harian, tetapi skrip hanya mengambil data jika sudah jatuh tempo (`INTERVAL_HARI`, bawaan 3, boleh 2). Tahan terhadap jadwal yang tertunda atau terlewat.
- Hari yang terlewat disusul: tiap putaran mengambil semua tanggal sejak data terakhir (maksimal 7 hari terbaru).
- Penyimpanan: file CSV di repositori, ditulis oleh workflow.
- Dashboard: Streamlit Community Cloud, membaca CSV dari repositori yang sama.
- Pengelompokan: pergerakan peringkat (baru masuk, naik, turun, bertahan) dibanding hari sebelumnya.
- Notifikasi: workflow memanggil Telegram `sendMessage` ke satu chat tetap (rahasia di GitHub Secrets). Bot tidak perlu menyala terus.
- Perintah interaktif bot (`/terpopuler`, `/ambil`) di luar cakupan awal (lihat Task 9).

## Goals, non-goals, anti-goals

- Goals: pengambilan otomatis tanpa laptop; notifikasi Telegram setiap putaran; dashboard menampilkan semua data dengan filter tanggal dan kelompok.
- Non-goals: perintah interaktif bot, klasifikasi topik artikel, edisi bahasa lain, database server.
- Anti-goals: data hilang diam-diam; token bocor ke repositori; pengambilan yang melanggar aturan API Wikimedia.

## Pendekatan yang dipertimbangkan

| Pendekatan | Kelebihan | Kekurangan |
|---|---|---|
| A. GitHub Actions + CSV di repo + Streamlit Cloud (pilihan) | Gratis, tanpa server, semua di satu repo, mudah dijelaskan di laporan | Jadwal bisa tertunda atau terlewat; dinonaktifkan setelah 60 hari repo tanpa aktivitas; dashboard tidur setelah 12 jam tanpa pengunjung; bot tidak interaktif |
| B. Server selalu menyala (PythonAnywhere, Render, Railway) dengan bot polling | Bot interaktif penuh | Batas paket gratis terkini belum dicek; perlu mengurus server |
| C. Serverless (cron + fungsi webhook + database terkelola) | Bisa interaktif tanpa server sendiri | Terlalu banyak komponen untuk tugas sekecil ini |

## Batasan yang diketahui

Jumlah baca adalah jumlah permintaan, bukan orang unik. Dashboard yang tidur bisa dibangunkan pengunjung dengan satu klik; buka sebelum presentasi.
