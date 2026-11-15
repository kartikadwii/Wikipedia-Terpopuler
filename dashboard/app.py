"""Dasbor Streamlit: artikel Wikipedia terpopuler (data dari CSV di repositori)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from analysis import KELOMPOK, tabel_harian, tren_artikel  # noqa: E402
from config import NAMA_CSV  # noqa: E402
from storage import muat  # noqa: E402


def lokasi_csv() -> Path:
    return Path(os.environ.get("DATA_DIR") or ROOT / "data") / NAMA_CSV


def hitung_metrik(semua: pd.DataFrame) -> tuple[int, int, int]:
    return len(semua), semua["tanggal"].nunique(), semua["artikel"].nunique()


@st.cache_data(ttl=300)
def baca_data(path: str) -> pd.DataFrame:
    return muat(Path(path))


st.set_page_config(page_title="Pemantau Wikipedia", layout="wide")
st.title("Pemantau Artikel Wikipedia Terpopuler")
st.caption(
    "Angka menunjukkan jumlah permintaan halaman (page views), "
    "bukan jumlah pengunjung unik."
)

semua = baca_data(str(lokasi_csv()))
if semua.empty:
    st.info("Belum ada data. Jalankan pengambilan data terlebih dahulu.")
    st.stop()

total, hari, unik = hitung_metrik(semua)
k1, k2, k3 = st.columns(3)
k1.metric("Total baris", total)
k2.metric("Hari tercakup", hari)
k3.metric("Artikel unik", unik)

tanggal_ada = sorted(set(semua["tanggal"]), reverse=True)
f1, f2 = st.columns(2)
tanggal = f1.selectbox("Tanggal", tanggal_ada, index=0)
kelompok = f2.multiselect("Kelompok", list(KELOMPOK), default=list(KELOMPOK))

tabel = tabel_harian(semua, tanggal)
tabel = tabel[tabel["kelompok"].isin(kelompok)]

st.subheader(f"Peringkat {tanggal}")
st.dataframe(tabel, hide_index=True)

st.subheader("Tren jumlah baca")
semua_judul = sorted(set(semua["artikel"]))
awal = list(tabel_harian(semua, tanggal).sort_values("peringkat")["artikel"].head(5))
pilihan = st.multiselect("Artikel", semua_judul, default=awal)
if pilihan:
    tren = tren_artikel(semua, pilihan).astype("float64")
    st.line_chart(tren)
else:
    st.info("Pilih setidaknya satu artikel untuk melihat tren.")

st.download_button(
    "Unduh CSV lengkap",
    data=semua.to_csv(index=False).encode("utf-8"),
    file_name=NAMA_CSV,
    mime="text/csv",
)
