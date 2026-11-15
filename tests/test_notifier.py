from datetime import date

import pytest
import requests

from analysis import Ringkasan
from notifier import NotifikasiGagal, kirim_pesan, susun_pesan, susun_pesan_gagal

URL = "https://dash.example/x"


def _ringkasan(**kw):
    dasar = dict(
        tanggal_awal=date(2026, 11, 1),
        tanggal_akhir=date(2026, 11, 7),
        jumlah_baris=350,
        data_awal=False,
        baru=["Artikel Baru"],
        naik_tertinggi=[("Artikel Naik", 30, 5)],
        teratas=("Artikel Teratas", 123456),
    )
    dasar.update(kw)
    return Ringkasan(**dasar)


class SesiPalsu:
    def __init__(self, ok=True, galat=None, json_ok=True):
        self.ok, self.galat, self.json_ok = ok, galat, json_ok
        self.panggilan = []

    def post(self, url, json=None, timeout=None):
        self.panggilan.append((url, json, timeout))
        if self.galat:
            raise self.galat
        return _Resp(self.ok, self.json_ok)


class _Resp:
    def __init__(self, ok, json_ok):
        self.ok, self._j = ok, json_ok
        self.status_code = 200 if ok else 500

    def json(self):
        return {"ok": self._j}


def test_pesan_memuat_rentang_tanggal_jumlah_baris_dan_url():
    p = susun_pesan(_ringkasan(), URL)
    for s in ["2026-11-01", "2026-11-07", "350", URL, "Artikel Teratas",
              "Artikel Baru", "Artikel Naik"]:
        assert s in p


def test_pesan_data_awal_tidak_menyebut_baru_masuk():
    p = susun_pesan(_ringkasan(data_awal=True, baru=["X1", "X2"]), URL)
    assert "data awal" in p.lower()
    assert "X1" not in p
    assert "baru" not in p.lower()


def test_pesan_menyebut_tanggal_dilewati():
    p = susun_pesan(_ringkasan(), URL, [date(2026, 11, 3)])
    assert "2026-11-03" in p


def test_pesan_tanpa_url_tetap_jalan():
    assert "http" not in susun_pesan(_ringkasan(), "")


def test_pesan_maksimal_4000_karakter():
    judul = ["J" * 500 + str(i) for i in range(50)]
    p = susun_pesan(_ringkasan(baru=judul, teratas=("T" * 5000, 1)), URL)
    assert len(p) <= 4000
    assert len(susun_pesan_gagal("g" * 9000)) <= 4000


def test_pesan_gagal_memuat_alasan():
    assert "boom" in susun_pesan_gagal("boom")


def test_kirim_pesan_memanggil_sendMessage():
    s = SesiPalsu()
    kirim_pesan("halo", "TOK", "123", sesi=s)
    url, isi, timeout = s.panggilan[0]
    assert url.endswith("/sendMessage")
    assert isi["chat_id"] == "123" and isi["text"] == "halo"
    assert timeout


def test_kirim_pesan_dipotong():
    s = SesiPalsu()
    kirim_pesan("a" * 9000, "TOK", "1", sesi=s)
    assert len(s.panggilan[0][1]["text"]) <= 4000


@pytest.mark.parametrize("sesi", [
    SesiPalsu(ok=False),
    SesiPalsu(json_ok=False),
    SesiPalsu(galat=requests.ConnectionError("https://api.telegram.org/botSECRET123/sendMessage")),
])
def test_kirim_pesan_gagal_melempar_dan_tidak_membocorkan_token(sesi):
    with pytest.raises(NotifikasiGagal) as e:
        kirim_pesan("x", "SECRET123", "1", sesi=sesi)
    assert "SECRET123" not in str(e.value)
    assert "api.telegram.org" not in str(e.value)
    assert e.value.__cause__ is None
