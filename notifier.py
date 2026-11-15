"""Notifikasi Telegram: susun pesan ringkasan dan kirim lewat Bot API."""
from datetime import date

import requests

from analysis import Ringkasan

BATAS_PESAN = 4000
_TIMEOUT = 15


class NotifikasiGagal(Exception):
    """Pesan Telegram gagal terkirim (tanpa URL atau token di teksnya)."""


def _potong(teks: str) -> str:
    if len(teks) <= BATAS_PESAN:
        return teks
    return teks[: BATAS_PESAN - 1] + "…"


def susun_pesan(
    ringkasan: Ringkasan,
    dashboard_url: str,
    tanggal_dilewati: list[date] | None = None,
) -> str:
    """Susun teks ringkasan harian (maks. 4000 karakter)."""
    baris = [
        f"Pemantau Wikipedia {ringkasan.tanggal_awal.isoformat()} "
        f"s.d. {ringkasan.tanggal_akhir.isoformat()}",
        f"Jumlah baris data: {ringkasan.jumlah_baris}",
    ]
    artikel, tayangan = ringkasan.teratas
    baris.append(f"Teratas: {artikel} ({tayangan} tayangan)")
    if ringkasan.data_awal:
        baris.append("Ini data awal; belum ada pembanding hari sebelumnya.")
    else:
        if ringkasan.baru:
            baris.append("Baru masuk: " + ", ".join(ringkasan.baru[:5]))
        for judul, dari, ke in ringkasan.naik_tertinggi[:3]:
            baris.append(f"Naik: {judul} (#{dari} -> #{ke})")
    if tanggal_dilewati:
        baris.append(
            "Tanggal dilewati: " + ", ".join(t.isoformat() for t in tanggal_dilewati)
        )
    if dashboard_url:
        baris.append(f"Dasbor: {dashboard_url}")
    return _potong("\n".join(baris))


def susun_pesan_gagal(alasan: str) -> str:
    """Pesan singkat saat putaran harian gagal."""
    return _potong(f"Pemantau Wikipedia gagal: {alasan}")


def kirim_pesan(teks: str, token: str, chat_id: str, sesi=None) -> None:
    """Kirim teks biasa ke Telegram; galat dilaporkan tanpa URL/token."""
    sesi = sesi if sesi is not None else requests
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = sesi.post(
            url, json={"chat_id": chat_id, "text": _potong(teks)}, timeout=_TIMEOUT
        )
        sukses = bool(resp.ok) and resp.json().get("ok") is True
    except (requests.RequestException, ValueError):
        raise NotifikasiGagal("Pengiriman notifikasi Telegram gagal.") from None
    if not sukses:
        raise NotifikasiGagal("Telegram menolak pesan notifikasi.")
