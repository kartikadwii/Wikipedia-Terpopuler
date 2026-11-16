"""Klien REST API pageviews Wikimedia (artikel terpopuler per hari, UTC)."""
import time
from dataclasses import dataclass
from datetime import date

import requests

_URL = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
    "{proyek}/all-access/{tahun:04d}/{bulan:02d}/{hari:02d}"
)
_PERCOBAAN = 3
_ABAIKAN = {"Halaman_Utama", "-", ""}


@dataclass
class ArtikelBaca:
    peringkat: int
    artikel: str
    jumlah_baca: int


def _layak(judul: str) -> bool:
    return judul not in _ABAIKAN and ":" not in judul


def ambil_top_artikel(
    tanggal: date,
    proyek: str,
    user_agent: str,
    jumlah: int = 50,
    sesi=None,
    jeda: float = 0.5,
) -> list[ArtikelBaca] | None:
    """Ambil artikel terpopuler pada `tanggal` (UTC).

    Mengembalikan None hanya bila HTTP 404 (data belum tersedia). Untuk 429/5xx
    dicoba ulang 3 kali dengan backoff; bila habis, atau status non-2xx lain,
    melempar requests.HTTPError.
    """
    if sesi is None:
        sesi = requests.Session()
    url = _URL.format(
        proyek=proyek, tahun=tanggal.year, bulan=tanggal.month, hari=tanggal.day
    )
    status = None
    for percobaan in range(_PERCOBAAN):
        time.sleep(jeda)
        resp = sesi.get(url, headers={"User-Agent": user_agent}, timeout=30)
        status = resp.status_code
        if status == 404:
            return None
        if 200 <= status < 300:
            break
        if status == 429 or status >= 500:
            if percobaan < _PERCOBAAN - 1:
                time.sleep(jeda * 2**percobaan)
            continue
        raise requests.HTTPError(f"Status HTTP {status} untuk {tanggal.isoformat()}")
    else:
        raise requests.HTTPError(
            f"Status HTTP {status} setelah {_PERCOBAAN} percobaan "
            f"untuk {tanggal.isoformat()}"
        )

    hasil = []
    try:
        daftar = resp.json()["items"][0]["articles"]
        for item in daftar:
            judul = item["article"]
            if not _layak(judul):
                continue
            hasil.append(
                ArtikelBaca(len(hasil) + 1, judul.replace("_", " "), int(item["views"]))
            )
            if len(hasil) >= jumlah:
                break
    except (KeyError, IndexError, TypeError, ValueError):
        raise requests.HTTPError("Respons tidak valid dari Wikimedia") from None
    return hasil
