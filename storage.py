"""Penyimpanan CSV (UTF-8) untuk artikel terpopuler."""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

KOLOM = ["tanggal", "peringkat", "artikel", "jumlah_baca", "diambil_pada"]
_KUNCI = ["tanggal", "artikel"]


def _kosong() -> pd.DataFrame:
    df = pd.DataFrame({k: pd.Series(dtype="object") for k in KOLOM})
    df["peringkat"] = df["peringkat"].astype("int64")
    df["jumlah_baca"] = df["jumlah_baca"].astype("int64")
    return df


def _normalkan(df: pd.DataFrame) -> pd.DataFrame:
    df = df[KOLOM].copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date
    df["peringkat"] = df["peringkat"].astype("int64")
    df["jumlah_baca"] = df["jumlah_baca"].astype("int64")
    df["artikel"] = df["artikel"].astype(str)
    df["diambil_pada"] = df["diambil_pada"].astype(str)
    return df.reset_index(drop=True)


def muat(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return _kosong()
    df = pd.read_csv(path, encoding="utf-8", dtype={"artikel": str, "diambil_pada": str}, keep_default_na=False)
    if df.empty:
        return _kosong()
    return _normalkan(df)


def tambah(path: Path, baris: pd.DataFrame) -> int:
    """Tambahkan baris baru (kunci: tanggal + artikel). Mengembalikan jumlah baris baru."""
    path = Path(path)
    ada = muat(path)
    if baris is None or len(baris) == 0:
        return 0
    baru = _normalkan(baris).drop_duplicates(subset=_KUNCI, keep="first")
    kunci_ada = set(zip(ada["tanggal"], ada["artikel"]))
    mask = [k not in kunci_ada for k in zip(baru["tanggal"], baru["artikel"])]
    baru = baru[mask]
    if baru.empty:
        return 0
    gabung = pd.concat([ada, baru], ignore_index=True) if not ada.empty else baru
    path.parent.mkdir(parents=True, exist_ok=True)
    gabung.to_csv(path, index=False, encoding="utf-8")
    return len(baru)


def tanggal_terakhir(df: pd.DataFrame) -> date | None:
    if df.empty:
        return None
    return max(df["tanggal"])


def waktu_run_terakhir(df: pd.DataFrame) -> date | None:
    if df.empty:
        return None
    return max(date.fromisoformat(str(s)) for s in df["diambil_pada"])


def sudah_jatuh_tempo(run_terakhir: date | None, hari_ini: date, interval_hari: int) -> bool:
    if run_terakhir is None:
        return True
    return (hari_ini - run_terakhir).days >= interval_hari


def tanggal_yang_perlu_diambil(
    terakhir: date | None, hari_ini: date, interval_hari: int, maks_hari: int
) -> list[date]:
    awal = terakhir + timedelta(days=1) if terakhir else hari_ini - timedelta(days=interval_hari)
    awal = max(awal, hari_ini - timedelta(days=maks_hari))
    akhir = hari_ini - timedelta(days=1)
    n = (akhir - awal).days + 1
    return [awal + timedelta(days=i) for i in range(max(n, 0))]
