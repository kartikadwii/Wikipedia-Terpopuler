"""Analisis pergerakan peringkat artikel terpopuler."""
from dataclasses import dataclass
from datetime import date

import pandas as pd

KELOMPOK = ("baru", "naik", "turun", "bertahan")

_KOLOM_KLASIFIKASI = ["artikel", "peringkat", "peringkat_sebelum", "selisih", "kelompok"]
_KOLOM_HARIAN = _KOLOM_KLASIFIKASI + ["jumlah_baca"]


def klasifikasi_pergerakan(sekarang: pd.DataFrame, sebelumnya: pd.DataFrame) -> pd.DataFrame:
    """Bandingkan peringkat sekarang dengan sebelumnya; selisih positif berarti naik."""
    if len(sebelumnya) > 0:
        peta = dict(zip(sebelumnya["artikel"], sebelumnya["peringkat"]))
    else:
        peta = {}
    hasil = sekarang[["artikel", "peringkat"]].copy()
    hasil["peringkat"] = hasil["peringkat"].astype("int64")
    hasil["peringkat_sebelum"] = pd.array(
        [peta.get(a, pd.NA) for a in hasil["artikel"]], dtype="Int64"
    )
    hasil["selisih"] = hasil["peringkat_sebelum"] - hasil["peringkat"]

    def kelompok(s):
        if pd.isna(s):
            return "baru"
        if s > 0:
            return "naik"
        if s < 0:
            return "turun"
        return "bertahan"

    hasil["kelompok"] = [kelompok(s) for s in hasil["selisih"]]
    hasil = hasil.sort_values("peringkat", kind="stable").reset_index(drop=True)
    return hasil[_KOLOM_KLASIFIKASI]


@dataclass
class Ringkasan:
    tanggal_awal: date
    tanggal_akhir: date
    jumlah_baris: int
    data_awal: bool
    baru: list[str]
    naik_tertinggi: list[tuple[str, int, int]]
    teratas: tuple[str, int]


def _sebelumnya_tersedia(semua: pd.DataFrame, tanggal: date) -> pd.DataFrame:
    lebih_awal = [t for t in set(semua["tanggal"]) if t < tanggal]
    if not lebih_awal:
        return semua.iloc[0:0]
    return semua[semua["tanggal"] == max(lebih_awal)]


def tabel_harian(semua: pd.DataFrame, tanggal: date) -> pd.DataFrame:
    """Klasifikasi untuk `tanggal` terhadap tanggal tersedia terakhir sebelumnya."""
    hari = semua[semua["tanggal"] == tanggal]
    if hari.empty:
        kosong = klasifikasi_pergerakan(hari, semua.iloc[0:0])
        kosong["jumlah_baca"] = pd.Series(dtype="int64")
        return kosong[_KOLOM_HARIAN]
    hasil = klasifikasi_pergerakan(hari, _sebelumnya_tersedia(semua, tanggal))
    baca = dict(zip(hari["artikel"], hari["jumlah_baca"]))
    hasil["jumlah_baca"] = pd.Series(
        [baca[a] for a in hasil["artikel"]], dtype="int64", index=hasil.index
    )
    return hasil[_KOLOM_HARIAN]


def ringkas_putaran(baris_baru: pd.DataFrame, semua: pd.DataFrame) -> Ringkasan:
    """Ringkas satu putaran pengambilan; `semua` sudah memuat `baris_baru`."""
    tanggal_awal = min(baris_baru["tanggal"])
    tanggal_akhir = max(baris_baru["tanggal"])
    data_awal = not any(t < tanggal_awal for t in semua["tanggal"])
    tabel = tabel_harian(semua, tanggal_akhir)
    puncak = tabel.sort_values("peringkat").iloc[0]
    teratas = (str(puncak["artikel"]), int(puncak["jumlah_baca"]))
    baru: list[str] = []
    naik: list[tuple[str, int, int]] = []
    if not data_awal:
        baru = tabel.loc[tabel["kelompok"] == "baru", "artikel"].head(5).tolist()
        n = tabel[tabel["kelompok"] == "naik"].sort_values(
            ["selisih", "peringkat"], ascending=[False, True]
        ).head(3)
        naik = [
            (str(r.artikel), int(r.peringkat_sebelum), int(r.peringkat))
            for r in n.itertuples()
        ]
    return Ringkasan(
        tanggal_awal=tanggal_awal,
        tanggal_akhir=tanggal_akhir,
        jumlah_baris=len(baris_baru),
        data_awal=data_awal,
        baru=baru,
        naik_tertinggi=naik,
        teratas=teratas,
    )


def tren_artikel(semua: pd.DataFrame, artikel: list[str]) -> pd.DataFrame:
    """Jumlah baca per tanggal untuk tiap artikel (Int64, <NA> bila tidak ada)."""
    indeks = sorted(set(semua["tanggal"]))
    hasil = pd.DataFrame(index=pd.Index(indeks, dtype="object", name="tanggal"))
    for judul in artikel:
        sub = semua[semua["artikel"] == judul].drop_duplicates("tanggal")
        peta = dict(zip(sub["tanggal"], sub["jumlah_baca"]))
        hasil[judul] = pd.array([peta.get(t, pd.NA) for t in indeks], dtype="Int64")
    return hasil
