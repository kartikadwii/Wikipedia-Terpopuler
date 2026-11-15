from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from config import NAMA_CSV  # noqa: E402
from storage import KOLOM, tambah  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")


def _contoh():
    import pandas as pd

    baris = [
        (date(2026, 11, 14), 1, "A", 100),
        (date(2026, 11, 14), 2, "B", 90),
        (date(2026, 11, 15), 1, "B", 120),
        (date(2026, 11, 15), 2, "C", 80),
    ]
    return pd.DataFrame(
        [
            {"tanggal": t, "peringkat": r, "artikel": a, "jumlah_baca": j, "diambil_pada": "2026-11-16"}
            for t, r, a, j in baris
        ],
        columns=KOLOM,
    )


def test_data_kosong_menampilkan_info(tmp_path, monkeypatch):
    (tmp_path / NAMA_CSV).write_text("", encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    at = AppTest.from_file(APP).run()
    assert not at.exception
    assert any("Belum ada data" in i.value for i in at.info)


def test_data_ada_menampilkan_tiga_metrik(tmp_path, monkeypatch):
    tambah(tmp_path / NAMA_CSV, _contoh())
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    at = AppTest.from_file(APP).run()
    assert not at.exception
    nilai = {m.label: m.value for m in at.metric}
    assert nilai == {"Total baris": "4", "Hari tercakup": "2", "Artikel unik": "3"}
