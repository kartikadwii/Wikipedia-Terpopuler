from datetime import date

import pandas as pd
import pytest

import analysis
from analysis import KELOMPOK, Ringkasan, klasifikasi_pergerakan, ringkas_putaran, tabel_harian, tren_artikel
from storage import KOLOM


def buat(*baris):
    """baris: (tanggal, peringkat, artikel, jumlah_baca)."""
    df = pd.DataFrame(
        [(t, p, a, j, "2026-01-01T00:00:00Z") for t, p, a, j in baris], columns=KOLOM
    )
    df["peringkat"] = df["peringkat"].astype("int64")
    df["jumlah_baca"] = df["jumlah_baca"].astype("int64")
    return df


def peringkat_saja(*pasangan):
    return pd.DataFrame(list(pasangan), columns=["artikel", "peringkat"]).astype({"peringkat": "int64"})


def test_klasifikasi_empat_kelompok():
    sekarang = peringkat_saja(("A", 2), ("B", 4), ("C", 3), ("D", 1))
    sebelumnya = peringkat_saja(("A", 5), ("B", 2), ("C", 3))
    hasil = klasifikasi_pergerakan(sekarang, sebelumnya)
    assert list(hasil.columns) == ["artikel", "peringkat", "peringkat_sebelum", "selisih", "kelompok"]
    assert list(hasil["artikel"]) == ["D", "A", "C", "B"]
    assert str(hasil["peringkat_sebelum"].dtype) == "Int64"
    assert str(hasil["selisih"].dtype) == "Int64"
    baris = hasil.set_index("artikel")
    assert baris.loc["A", "kelompok"] == "naik" and baris.loc["A", "selisih"] == 3
    assert baris.loc["B", "kelompok"] == "turun" and baris.loc["B", "selisih"] == -2
    assert baris.loc["C", "kelompok"] == "bertahan" and baris.loc["C", "selisih"] == 0
    assert baris.loc["D", "kelompok"] == "baru"
    assert pd.isna(baris.loc["D", "peringkat_sebelum"]) and pd.isna(baris.loc["D", "selisih"])
    assert set(hasil["kelompok"]) <= set(KELOMPOK)


def test_sebelumnya_kosong_semua_baru():
    sekarang = peringkat_saja(("A", 1), ("B", 2))
    hasil = klasifikasi_pergerakan(sekarang, pd.DataFrame(columns=["artikel", "peringkat"]))
    assert list(hasil["kelompok"]) == ["baru", "baru"]
    assert hasil["peringkat_sebelum"].isna().all()
    assert hasil["selisih"].isna().all()
    assert str(hasil["selisih"].dtype) == "Int64"


def test_ringkas_putaran_data_awal():
    semua = buat(*[(date(2026, 1, 10), i, f"A{i}", 100 - i) for i in range(1, 51)])
    r = ringkas_putaran(semua, semua)
    assert isinstance(r, Ringkasan)
    assert r.data_awal is True
    assert r.baru == []
    assert r.naik_tertinggi == []
    assert r.jumlah_baris == 50
    assert r.tanggal_awal == r.tanggal_akhir == date(2026, 1, 10)
    assert r.teratas == ("A1", 99)


def test_ringkas_putaran_data_awal_beberapa_tanggal():
    semua = buat(
        (date(2026, 1, 9), 1, "X", 10),
        (date(2026, 1, 10), 1, "Y", 20),
    )
    r = ringkas_putaran(semua, semua)
    assert r.data_awal is True
    assert r.baru == [] and r.naik_tertinggi == []
    assert (r.tanggal_awal, r.tanggal_akhir) == (date(2026, 1, 9), date(2026, 1, 10))


def test_ringkas_putaran_isi():
    kemarin = [(date(2026, 1, 9), i, f"L{i}", 50) for i in range(1, 11)]
    hari = [
        (date(2026, 1, 10), 1, "N1", 900),
        (date(2026, 1, 10), 2, "N2", 800),
        (date(2026, 1, 10), 3, "N3", 700),
        (date(2026, 1, 10), 4, "N4", 600),
        (date(2026, 1, 10), 5, "N5", 500),
        (date(2026, 1, 10), 6, "N6", 400),
        (date(2026, 1, 10), 7, "L10", 300),  # 10 -> 7, naik 3
        (date(2026, 1, 10), 8, "L9", 200),  # 9 -> 8, naik 1
        (date(2026, 1, 10), 9, "L5", 150),  # 5 -> 9, turun
        (date(2026, 1, 10), 10, "L8", 100),  # 8 -> 10, turun
        (date(2026, 1, 10), 11, "L2", 90),  # 2 -> 11, turun
        (date(2026, 1, 10), 12, "L1", 80),  # 1 -> 12, turun
    ]
    baru_df = buat(*hari)
    semua = pd.concat([buat(*kemarin), baru_df], ignore_index=True)
    semua_asli = semua.copy()
    r = ringkas_putaran(baru_df, semua)
    assert r.data_awal is False
    assert r.baru == ["N1", "N2", "N3", "N4", "N5"]  # N6 dipotong (maks 5)
    assert r.naik_tertinggi == [("L10", 10, 7), ("L9", 9, 8)]
    assert len(r.naik_tertinggi) <= 3
    assert r.teratas == ("N1", 900)
    assert r.jumlah_baris == 12
    pd.testing.assert_frame_equal(semua, semua_asli)


def test_ringkas_putaran_naik_dibatasi_tiga():
    kemarin = buat(*[(date(2026, 1, 9), i, f"L{i}", 5) for i in range(1, 9)])
    hari = buat(*[(date(2026, 1, 10), i, f"L{9 - i}", 5) for i in range(1, 9)])  # urutan terbalik
    r = ringkas_putaran(hari, pd.concat([kemarin, hari], ignore_index=True))
    assert len(r.naik_tertinggi) == 3
    assert r.naik_tertinggi == [("L8", 8, 1), ("L7", 7, 2), ("L6", 6, 3)]


def test_tabel_harian_memakai_tanggal_sebelumnya_yang_tersedia():
    semua = buat(
        (date(2026, 1, 12), 1, "A", 10),
        (date(2026, 1, 12), 2, "B", 9),
        (date(2026, 1, 14), 1, "B", 30),
        (date(2026, 1, 14), 2, "A", 20),
        (date(2026, 1, 14), 3, "C", 5),
    )
    hasil = tabel_harian(semua, date(2026, 1, 14))
    assert list(hasil.columns) == [
        "artikel", "peringkat", "peringkat_sebelum", "selisih", "kelompok", "jumlah_baca"
    ]
    baris = hasil.set_index("artikel")
    assert list(hasil["artikel"]) == ["B", "A", "C"]
    assert baris.loc["B", "kelompok"] == "naik" and baris.loc["B", "peringkat_sebelum"] == 2
    assert baris.loc["A", "kelompok"] == "turun" and baris.loc["A", "selisih"] == -1
    assert baris.loc["C", "kelompok"] == "baru"
    assert baris.loc["B", "jumlah_baca"] == 30


def test_tabel_harian_tanpa_pembanding_dan_tanggal_kosong():
    semua = buat((date(2026, 1, 12), 1, "A", 10))
    hasil = tabel_harian(semua, date(2026, 1, 12))
    assert list(hasil["kelompok"]) == ["baru"]
    kosong = tabel_harian(semua, date(2026, 1, 20))
    assert kosong.empty
    assert list(kosong.columns) == list(hasil.columns)


def test_tren_artikel_judul_tidak_ada():
    semua = buat(
        (date(2026, 1, 12), 1, "A", 10),
        (date(2026, 1, 13), 1, "A", 12),
        (date(2026, 1, 13), 2, "B", 7),
    )
    hasil = tren_artikel(semua, ["A", "B", "Tidak Ada"])
    assert list(hasil.columns) == ["A", "B", "Tidak Ada"]
    assert list(hasil.index) == [date(2026, 1, 12), date(2026, 1, 13)]
    assert hasil["A"].tolist() == [10, 12]
    assert pd.isna(hasil.loc[date(2026, 1, 12), "B"]) and hasil.loc[date(2026, 1, 13), "B"] == 7
    assert hasil["Tidak Ada"].isna().all()
    assert str(hasil["A"].dtype) == "Int64"
