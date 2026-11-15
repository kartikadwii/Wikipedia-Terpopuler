from datetime import date

import requests

from config import NAMA_CSV, Pengaturan
from notifier import NotifikasiGagal
from run_scrape import jalankan
from storage import muat
from wiki_client import ArtikelBaca

HARI_INI = date(2026, 11, 10)


def _pengaturan(tmp_path, **kw):
    return Pengaturan(bot_token="rahasia-token", chat_id="123", data_dir=tmp_path / "data", **kw)


class Klien:
    def __init__(self, tidak_ada=(), galat=()):
        self.tidak_ada, self.galat, self.panggilan = set(tidak_ada), set(galat), []

    def __call__(self, tanggal, proyek, user_agent, jumlah=50):
        self.panggilan.append(tanggal)
        if tanggal in self.galat:
            raise requests.ConnectionError("gagal")
        if tanggal in self.tidak_ada:
            return None
        return [ArtikelBaca(i, f"A{i}", 1000 - i) for i in range(1, 51)]


class Kirim:
    def __init__(self, galat=None):
        self.pesan, self.galat = [], galat

    def __call__(self, teks, token, chat_id):
        self.pesan.append(teks)
        if self.galat:
            raise self.galat


def _csv(p):
    return p.data_dir / NAMA_CSV


def test_belum_jatuh_tempo_keluar_0_tanpa_memanggil_klien(tmp_path):
    p, k, s = _pengaturan(tmp_path), Klien(), Kirim()
    assert jalankan(HARI_INI, p, k, s) == 0
    k.panggilan.clear()
    assert jalankan(date(2026, 11, 11), p, k, s) == 0
    assert k.panggilan == [] and len(s.pesan) == 1


def test_putaran_normal(tmp_path):
    p, k, s = _pengaturan(tmp_path), Klien(), Kirim()
    assert jalankan(HARI_INI, p, k, s) == 0
    assert k.panggilan == [date(2026, 11, 7), date(2026, 11, 8), date(2026, 11, 9)]
    df = muat(_csv(p))
    assert len(df) == 150
    assert set(df["diambil_pada"]) == {"2026-11-10"}
    assert len(s.pesan) == 1 and "data awal" in s.pesan[0]


def test_jeda_panjang_hanya_tujuh_hari(tmp_path):
    p, k, s = _pengaturan(tmp_path), Klien(), Kirim()
    jalankan(HARI_INI, p, k, s)
    k.panggilan.clear()
    assert jalankan(date(2026, 12, 25), p, k, s) == 0
    assert len(k.panggilan) == 7


def test_tanggal_404_dilewati(tmp_path):
    p, s = _pengaturan(tmp_path), Kirim()
    k = Klien(tidak_ada=[date(2026, 11, 8)])
    assert jalankan(HARI_INI, p, k, s) == 0
    assert len(muat(_csv(p))) == 100
    assert "2026-11-08" in s.pesan[0]


def test_galat_klien_dianggap_dilewati(tmp_path):
    p, s = _pengaturan(tmp_path), Kirim()
    k = Klien(galat=[date(2026, 11, 9)])
    assert jalankan(HARI_INI, p, k, s) == 0
    assert len(muat(_csv(p))) == 100
    assert "2026-11-09" in s.pesan[0]


def test_semua_tanggal_gagal(tmp_path):
    p, s = _pengaturan(tmp_path), Kirim()
    k = Klien(tidak_ada=[date(2026, 11, 7), date(2026, 11, 8)], galat=[date(2026, 11, 9)])
    assert jalankan(HARI_INI, p, k, s) == 1
    assert not _csv(p).exists()
    assert len(s.pesan) == 1 and "gagal" in s.pesan[0]


def test_notifikasi_gagal_data_tetap_tersimpan(tmp_path):
    p, k = _pengaturan(tmp_path), Klien()
    s = Kirim(galat=NotifikasiGagal("x"))
    assert jalankan(HARI_INI, p, k, s) == 0
    assert len(muat(_csv(p))) == 150


def test_diulang_dengan_paksa_tidak_menggandakan_data(tmp_path):
    p, k, s = _pengaturan(tmp_path), Klien(), Kirim()
    jalankan(HARI_INI, p, k, s)
    k.panggilan.clear()
    assert jalankan(HARI_INI, p, k, s) == 0
    assert k.panggilan == []
    assert jalankan(HARI_INI, p, k, s, paksa=True) == 0
    assert k.panggilan == []
    assert len(muat(_csv(p))) == 150
    assert len(s.pesan) == 1
