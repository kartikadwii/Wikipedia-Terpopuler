from datetime import date

import pytest
import requests

import wiki_client
from wiki_client import ArtikelBaca, ambil_top_artikel


class ResponPalsu:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class SesiPalsu:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.panggilan = []

    def get(self, url, headers=None, timeout=None):
        self.panggilan.append({"url": url, "headers": headers, "timeout": timeout})
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


def _payload(judul):
    arts = [
        {"article": j, "views": 1000 - i, "rank": i + 1} for i, j in enumerate(judul)
    ]
    return {"items": [{"articles": arts}]}


@pytest.fixture(autouse=True)
def tanpa_tidur(monkeypatch):
    monkeypatch.setattr(wiki_client.time, "sleep", lambda s: None)


TGL = date(2026, 3, 5)


def _ambil(sesi, **kw):
    return ambil_top_artikel(TGL, "id.wikipedia", "UA-uji/1.0", sesi=sesi, **kw)


def test_parse_saring_dan_nomori_ulang():
    judul = ["Halaman_Utama", "Istimewa:Pencarian", "-", "", "Joko_Widodo", "Bali"]
    sesi = SesiPalsu(ResponPalsu(200, _payload(judul)))
    hasil = _ambil(sesi)
    assert hasil == [
        ArtikelBaca(1, "Joko Widodo", 996),
        ArtikelBaca(2, "Bali", 995),
    ]
    assert sesi.panggilan[0]["url"] == (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
        "id.wikipedia/all-access/2026/03/05"
    )


def test_dibatasi_jumlah():
    sesi = SesiPalsu(ResponPalsu(200, _payload([f"A{i}" for i in range(200)])))
    assert len(_ambil(sesi, jumlah=50)) == 50


def test_kurang_dari_jumlah_tidak_error():
    sesi = SesiPalsu(ResponPalsu(200, _payload([f"A{i}" for i in range(10)])))
    assert len(_ambil(sesi, jumlah=50)) == 10


def test_404_mengembalikan_none():
    assert _ambil(SesiPalsu(ResponPalsu(404))) is None


def test_retry_429_lalu_berhasil():
    sesi = SesiPalsu(ResponPalsu(429), ResponPalsu(200, _payload(["Bali"])))
    hasil = _ambil(sesi, jeda=0)
    assert hasil == [ArtikelBaca(1, "Bali", 1000)]
    assert len(sesi.panggilan) == 2


def test_retry_habis_melempar_error():
    sesi = SesiPalsu(ResponPalsu(503))
    with pytest.raises(requests.HTTPError):
        _ambil(sesi, jeda=0)
    assert len(sesi.panggilan) == 3


def test_status_lain_melempar_error():
    with pytest.raises(requests.HTTPError):
        _ambil(SesiPalsu(ResponPalsu(403)))


def test_user_agent_dikirim():
    sesi = SesiPalsu(ResponPalsu(200, _payload(["Bali"])))
    _ambil(sesi)
    assert sesi.panggilan[0]["headers"]["User-Agent"] == "UA-uji/1.0"


@pytest.mark.parametrize("data", [{"items": []}, {}, None, {"items": [{}]}])
def test_payload_tidak_valid_jadi_http_error(data):
    sesi = SesiPalsu(ResponPalsu(200, data))
    with pytest.raises(requests.RequestException):
        _ambil(sesi)
