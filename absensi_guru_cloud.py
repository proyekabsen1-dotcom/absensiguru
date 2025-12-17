import streamlit as st
import pandas as pd
import json
from datetime import datetime
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
# SECRETS STREAMLIT
# =====================================================
SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])

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
# DATA GURU
# =====================================================
GURU_LIST = [
    "Yolan", "Husnia", "Rima", "Rifa",
    "Sela", "Ustadz A", "Ustadz B", "Ustadz C"
]

# =====================================================
# FUNCTIONS
# =====================================================
@st.cache_data(ttl=30)
def load_data():
    data = ws.get_all_records()
    return pd.DataFrame(data)

def sudah_absen_hari_ini(df, nama):
    if df.empty:
        return False
    today = datetime.now(TZ).date()
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce").dt.date
    return ((df["Nama Guru"] == nama) & (df["Tanggal"] == today)).any()

def simpan_absen(row):
    ws.append_row(row)
    load_data.clear()

def buat_nomor_urut(df):
    df = df.copy()
    df.reset_index(drop=True, inplace=True)
    df.insert(0, "No", range(1, len(df) + 1))
    return df

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
    status = st.selectbox("Status", ["Hadir", "Izin", "Cuti", "Tidak Hadir"])
    ket = st.text_input("Keterangan (opsional)")

    if st.button("✅ Simpan Absensi"):
        if not lat or not lon:
            st.error("❌ Latitude dan Longitude wajib diisi")
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

    password = st.sidebar.text_input("Masukkan Kode Admin", type="password")
    if password != "bkq2025":
        st.warning("Masukkan kode admin untuk melihat rekap.")
        st.stop()

    st.header("📑 Rekap Absensi Guru")

    df = load_data()
    if df.empty:
        st.info("Belum ada data absensi.")
        st.stop()

    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce")
    df = df[df["Tanggal"].notna()]

    menu_rekap = st.selectbox(
        "Pilih Jenis Rekap",
        ["📅 Harian", "📆 Bulanan", "👤 Per Guru"]
    )

    st.divider()

    # =======================
    # HARIAN
    # =======================
    if menu_rekap == "📅 Harian":
        tgl = st.date_input("Pilih Tanggal", datetime.now().date())
        df_harian = df[df["Tanggal"].dt.date == tgl]

        if not df_harian.empty:
            df_harian = buat_nomor_urut(df_harian)
            st.dataframe(df_harian, use_container_width=True)

            csv = df_harian.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Unduh Rekap Harian (CSV)",
                csv,
                "rekap_harian.csv",
                "text/csv"
            )
        else:
            st.info("Tidak ada data pada tanggal ini.")

    # =======================
    # BULANAN
    # =======================
    elif menu_rekap == "📆 Bulanan":
        bulan_list = sorted(df["Tanggal"].dt.to_period("M").astype(str).unique())
        bulan = st.selectbox("Pilih Bulan", bulan_list)

        df_bulan = df[df["Tanggal"].dt.to_period("M").astype(str) == bulan]

        if not df_bulan.empty:
            df_bulan = buat_nomor_urut(df_bulan)
            st.dataframe(df_bulan, use_container_width=True)

            csv = df_bulan.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Unduh Rekap Bulanan (CSV)",
                csv,
                f"rekap_bulanan_{bulan}.csv",
                "text/csv"
            )
        else:
            st.info("Tidak ada data pada bulan ini.")

    # =======================
    # PER GURU
    # =======================
    elif menu_rekap == "👤 Per Guru":
        guru = st.selectbox("Pilih Guru", sorted(df["Nama Guru"].unique()))
        df_guru = df[df["Nama Guru"] == guru]

        if not df_guru.empty:
            df_guru = buat_nomor_urut(df_guru)
            st.dataframe(df_guru, use_container_width=True)

            csv = df_guru.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Unduh Rekap Guru (CSV)",
                csv,
                f"rekap_{guru}.csv",
                "text/csv"
            )
        else:
            st.info("Tidak ada data untuk guru ini.")
