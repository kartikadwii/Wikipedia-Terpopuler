"""Orkestrasi satu putaran: ambil data, simpan ke CSV, ringkas, kirim notifikasi."""
import argparse
import logging
import sys
from datetime import date, datetime, timezone

import pandas as pd
import requests

from analysis import ringkas_putaran
from config import NAMA_CSV, Pengaturan, ambil_pengaturan
from notifier import NotifikasiGagal, kirim_pesan, susun_pesan, susun_pesan_gagal
from storage import (
    KOLOM,
    muat,
    sudah_jatuh_tempo,
    tambah,
    tanggal_terakhir,
    tanggal_yang_perlu_diambil,
    waktu_run_terakhir,
)
from wiki_client import ambil_top_artikel

log = logging.getLogger(__name__)


def _kirim_aman(kirim, teks: str, pengaturan: Pengaturan) -> None:
    try:
        kirim(teks, pengaturan.bot_token, pengaturan.chat_id)
    except NotifikasiGagal:
        log.warning("Notifikasi gagal terkirim; data tetap tersimpan.")


def jalankan(
    hari_ini: date,
    pengaturan: Pengaturan,
    klien=ambil_top_artikel,
    kirim=kirim_pesan,
    paksa: bool = False,
) -> int:
    path = pengaturan.data_dir / NAMA_CSV
    pengaturan.data_dir.mkdir(parents=True, exist_ok=True)
    df = muat(path)

    if not paksa and not sudah_jatuh_tempo(
        waktu_run_terakhir(df), hari_ini, pengaturan.interval_hari
    ):
        log.info("Belum jatuh tempo; tidak ada yang dikerjakan.")
        return 0

    tanggal_perlu = tanggal_yang_perlu_diambil(
        tanggal_terakhir(df), hari_ini, pengaturan.interval_hari, pengaturan.maks_hari_susul
    )
    if not tanggal_perlu:
        log.info("Tidak ada tanggal yang perlu diambil.")
        return 0

    potongan = []
    dilewati: list[date] = []
    for tgl in sorted(tanggal_perlu):
        try:
            hasil = klien(
                tgl, pengaturan.proyek, pengaturan.user_agent, pengaturan.jumlah_teratas
            )
        except requests.RequestException as e:
            log.warning("Gagal mengambil %s (%s); dilewati.", tgl.isoformat(), type(e).__name__)
            dilewati.append(tgl)
            continue
        if hasil is None:
            log.warning("Data %s belum tersedia; dilewati.", tgl.isoformat())
            dilewati.append(tgl)
            continue
        potongan.append(
            pd.DataFrame(
                {
                    "tanggal": [tgl] * len(hasil),
                    "peringkat": [a.peringkat for a in hasil],
                    "artikel": [a.artikel for a in hasil],
                    "jumlah_baca": [a.jumlah_baca for a in hasil],
                    "diambil_pada": [hari_ini.isoformat()] * len(hasil),
                },
                columns=KOLOM,
            )
        )

    baris_baru = pd.concat(potongan, ignore_index=True) if potongan else pd.DataFrame(columns=KOLOM)
    if baris_baru.empty:
        log.error("Semua tanggal gagal diambil.")
        daftar = ", ".join(t.isoformat() for t in dilewati)
        _kirim_aman(kirim, susun_pesan_gagal(f"tidak ada data untuk {daftar}"), pengaturan)
        return 1

    tambah(path, baris_baru)
    semua = muat(path)
    ringkasan = ringkas_putaran(baris_baru, semua)
    _kirim_aman(kirim, susun_pesan(ringkasan, pengaturan.dashboard_url, dilewati), pengaturan)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Pemantau Wikipedia terpopuler")
    parser.add_argument("--paksa", action="store_true", help="abaikan pemeriksaan jatuh tempo")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        pengaturan = ambil_pengaturan()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    hari_ini = datetime.now(timezone.utc).date()
    sys.exit(jalankan(hari_ini, pengaturan, paksa=args.paksa))


if __name__ == "__main__":
    main()
