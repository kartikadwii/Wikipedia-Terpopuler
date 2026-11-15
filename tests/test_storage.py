from datetime import date

import pandas as pd

from storage import (
    KOLOM,
    muat,
    sudah_jatuh_tempo,
    tambah,
    tanggal_yang_perlu_diambil,
)


def _baris(*item):
    return pd.DataFrame(
        [
            {"tanggal": t, "peringkat": r, "artikel": a, "jumlah_baca": j, "diambil_pada": "2026-11-15"}
            for t, r, a, j in item
        ],
        columns=KOLOM,
    )


def test_muat_file_belum_ada(tmp_path):
    df = muat(tmp_path / "tidak_ada.csv")
    assert df.empty
    assert list(df.columns) == KOLOM


def test_tambah_tidak_menggandakan(tmp_path):
    f = tmp_path / "d.csv"
    b = _baris((date(2026, 11, 14), 1, "A", 100), (date(2026, 11, 14), 2, "B", 90))
    assert tambah(f, b) == 2
    assert tambah(f, b) == 0
    assert len(muat(f)) == 2


def test_judul_karakter_khusus_utuh(tmp_path):
    f = tmp_path / "d.csv"
    judul = 'Soekarno, "Bung" Karno — Édith'
    tambah(f, _baris((date(2026, 11, 14), 1, judul, 5)))
    df = muat(f)
    assert df["artikel"].iloc[0] == judul
    assert df["tanggal"].iloc[0] == date(2026, 11, 14)
    assert int(df["peringkat"].iloc[0]) == 1


def test_tanggal_pertama_kali():
    assert tanggal_yang_perlu_diambil(None, date(2026, 11, 15), 3, 7) == [
        date(2026, 11, 12), date(2026, 11, 13), date(2026, 11, 14)
    ]


def test_tanggal_lanjut_setelah_terakhir():
    hi = date(2026, 11, 15)
    assert tanggal_yang_perlu_diambil(date(2026, 11, 11), hi, 3, 7) == [
        date(2026, 11, 12), date(2026, 11, 13), date(2026, 11, 14)
    ]
    assert tanggal_yang_perlu_diambil(date(2026, 11, 14), hi, 3, 7) == []


def test_tanggal_dibatasi_maks_hari():
    hasil = tanggal_yang_perlu_diambil(date(2026, 11, 1), date(2026, 11, 15), 3, 7)
    assert hasil == [date(2026, 11, d) for d in range(8, 15)]


def test_jatuh_tempo():
    assert sudah_jatuh_tempo(None, date(2026, 11, 15), 3)
    assert sudah_jatuh_tempo(date(2026, 11, 12), date(2026, 11, 15), 3)
    assert not sudah_jatuh_tempo(date(2026, 11, 12), date(2026, 11, 14), 3)
    assert sudah_jatuh_tempo(date(2026, 11, 12), date(2026, 11, 14), 2)


def test_judul_token_na_utuh_dan_tidak_menggandakan(tmp_path):
    f = tmp_path / "d.csv"
    judul = ["Null", "NA", "NaN", "None", "Nan"]
    b = _baris(*[(date(2026, 11, 14), i + 1, j, 10) for i, j in enumerate(judul)])
    assert tambah(f, b) == 5
    df = muat(f)
    assert list(df["artikel"]) == judul
    assert df["peringkat"].dtype == "int64" and df["jumlah_baca"].dtype == "int64"
    assert tambah(f, b) == 0
    assert len(muat(f)) == 5
