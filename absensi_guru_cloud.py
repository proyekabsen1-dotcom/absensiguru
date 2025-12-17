import streamlit as st
import pandas as pd
import json
from datetime import datetime, time as dt_time
import pytz

import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Absensi Guru SD Tahfidz BKQ",
    layout="centered"
)

TZ = pytz.timezone("Asia/Jakarta")

# =====================================================
# SECRETS (WAJIB ADA DI STREAMLIT)
# =====================================================
SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]

service_account_info = json.loads(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"]
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# =====================================================
# GOOGLE SHEETS AUTH
# =====================================================
creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=SCOPES
)

gc = gspread.authorize(creds)
sh = gc.open_by_url(SPREADSHEET_URL)

SHEET_NAME = "Absensi"

try:
    ws = sh.worksheet(SHEET_NAME)
except:
    ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=20)
    ws.append_row([
        "Tanggal",
        "Nama Guru",
        "Status",
        "Jam",
        "Latitude",
        "Longitude",
        "Keterangan"
    ])

# =====================================================
# DATA
# =====================================================
GURU_LIST = [
    "Yolan",
    "Husnia",
    "Rima",
    "Rifa",
    "Sela",
    "Ustadz A",
    "Ustadz B",
    "Ustadz C"
]

# =====================================================
# FUNCTIONS
# =====================================================
@st.cache_data(ttl=30)
def load_data():
    data = ws.get_all_records()
    return pd.DataFrame(data)

def sudah_absen_hari_ini(df, nama):
    today = datetime.now(TZ).date()
    if df.empty:
        return False
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date
    return ((df["Nama Guru"] == nama) & (df["Tanggal"] == today)).any()

def simpan_absen(row):
    ws.append_row(row)
    load_data.clear()

# =====================================================
# UI
# =====================================================
st.title("📍 Absensi Guru SD Tahfidz BKQ")
st.caption("Absensi berbasis lokasi (Latitude & Longitude)")

menu = st.sidebar.radio("Menu", ["Absensi", "Rekap"])

# =====================================================
# ABSENSI
# =====================================================
if menu == "Absensi":
    st.subheader("📝 Form Absensi")

    nama = st.selectbox("Nama Guru", GURU_LIST)

    lat = st.text_input("Latitude (contoh: -0.94924)")
    lon = st.text_input("Longitude (contoh: 100.35427)")

    status = st.selectbox(
        "Status",
        ["Hadir", "Izin", "Cuti", "Tidak Hadir"]
    )

    ket = st.text_input("Keterangan (opsional)")

    if st.button("✅ Simpan Absensi"):
        if not lat or not lon:
            st.error("❌ Lokasi (Latitude & Longitude) wajib diisi")
            st.stop()

        df = load_data()
        if sudah_absen_hari_ini(df, nama):
            st.error("❌ Guru ini sudah absen hari ini")
            st.stop()

        now = datetime.now(TZ)

        simpan_absen([
            now.strftime("%Y-%m-%d"),
            nama,
            status,
            now.strftime("%H:%M:%S"),
            lat,
            lon,
            ket
        ])

        st.success("✅ Absensi berhasil disimpan")

# =====================================================
# REKAP
# =====================================================
elif menu == "Rekap":
    st.subheader("📊 Rekap Absensi")

    password = st.text_input("Password Admin", type="password")
    if password != "bkq2025":
        st.warning("Masukkan password admin")
        st.stop()

    df = load_data()

    if df.empty:
        st.info("Belum ada data absensi")
        st.stop()

    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce")

    jenis = st.selectbox(
        "Jenis Rekap",
        ["Harian", "Bulanan", "Per Guru"]
    )

    if jenis == "Harian":
        tgl = st.date_input("Pilih Tanggal", datetime.now(TZ).date())
        hasil = df[df["Tanggal"].dt.date == tgl]

    elif jenis == "Bulanan":
        bulan = st.selectbox(
            "Pilih Bulan",
            sorted(df["Tanggal"].dt.to_period("M").astype(str).unique())
        )
        hasil = df[df["Tanggal"].dt.to_period("M").astype(str) == bulan]

    else:
        guru = st.selectbox("Pilih Guru", sorted(df["Nama Guru"].unique()))
        hasil = df[df["Nama Guru"] == guru]

    st.dataframe(hasil, use_container_width=True)
