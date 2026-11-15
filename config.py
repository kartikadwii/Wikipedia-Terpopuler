"""Pengaturan aplikasi, dibaca dari variabel lingkungan."""
import os
from dataclasses import dataclass, field
from pathlib import Path

NAMA_CSV = "top_artikel.csv"


def _user_agent_bawaan() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY") or "OWNER/REPO"
    return f"PemantauWikipediaTerpopuler/1.0 (+https://github.com/{repo}; tugas kuliah)"


@dataclass
class Pengaturan:
    bot_token: str = field(repr=False)
    chat_id: str
    interval_hari: int = 3
    jumlah_teratas: int = 50
    maks_hari_susul: int = 7
    proyek: str = "id.wikipedia"
    user_agent: str = ""
    dashboard_url: str = ""
    data_dir: Path = Path("data")


def _env(nama: str) -> str:
    return (os.environ.get(nama) or "").strip()


def ambil_pengaturan() -> Pengaturan:
    token = _env("BOT_TOKEN")
    chat_id = _env("CHAT_ID")
    if not token:
        raise ValueError("BOT_TOKEN wajib diisi (variabel lingkungan kosong atau hilang)")
    if not chat_id:
        raise ValueError("CHAT_ID wajib diisi (variabel lingkungan kosong atau hilang)")

    mentah = _env("INTERVAL_HARI")
    try:
        interval = int(mentah) if mentah else 3
    except ValueError:
        raise ValueError("INTERVAL_HARI harus berupa bilangan bulat") from None
    if interval < 1:
        raise ValueError("INTERVAL_HARI minimal 1")

    return Pengaturan(
        bot_token=token,
        chat_id=chat_id,
        interval_hari=interval,
        user_agent=_env("USER_AGENT") or _user_agent_bawaan(),
        dashboard_url=_env("DASHBOARD_URL"),
        data_dir=Path(_env("DATA_DIR") or "data"),
    )
