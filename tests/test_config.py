import pytest

from config import ambil_pengaturan

SEMUA = ["BOT_TOKEN", "CHAT_ID", "INTERVAL_HARI", "DASHBOARD_URL", "USER_AGENT", "DATA_DIR"]


@pytest.fixture(autouse=True)
def bersihkan_env(monkeypatch):
    for k in SEMUA:
        monkeypatch.delenv(k, raising=False)


def test_ambil_pengaturan_bawaan(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "rahasia")
    monkeypatch.setenv("CHAT_ID", "123")
    p = ambil_pengaturan()
    assert p.jumlah_teratas == 50
    assert p.interval_hari == 3


def test_ambil_pengaturan_menolak_interval_nol_dan_token_kosong(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "rahasia")
    monkeypatch.setenv("CHAT_ID", "123")
    monkeypatch.setenv("INTERVAL_HARI", "0")
    with pytest.raises(ValueError):
        ambil_pengaturan()
    monkeypatch.delenv("INTERVAL_HARI")
    monkeypatch.delenv("BOT_TOKEN")
    with pytest.raises(ValueError):
        ambil_pengaturan()
    monkeypatch.setenv("BOT_TOKEN", "")
    with pytest.raises(ValueError):
        ambil_pengaturan()
