import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from google.oauth2.service_account import Credentials
import gspread

# ==============================
# CONFIG
# ==============================
st.set_page_config(
    page_title="Absensi Guru BKQ",
    layout="centered"
)

st.title("📍 Absensi Guru SD Tahfidz BKQ")
st.caption("Absensi berbasis lokasi GPS")

TZ = pytz.timezone("Asia/Jakarta")

# ==============================
# GOOGLE SHEETS
# ==============================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"],
    scopes=SCOPES
)

gc = gspread.authorize(creds)
sh = gc.open_by_url(st.secrets["SPREADSHEET_URL"])

try:
    ws = sh.worksheet("Absensi")
except:
    ws = sh.add_worksheet(title="Absensi", rows="2000", cols="10")
    ws.append_row([
        "No","Tanggal","Nama Guru",
        "Jam Masuk","Latitude","Longitude","Link Maps"
    ])

# ==============================
# DATA GURU
# ==============================
GURU_LIST = [
    "Yolan","Husnia","Rima","Rifa",
    "Sela","Ustadz A","Ustadz B","Ustadz C"
]

# ==============================
# LOAD DATA
# ==============================
def load_df():
    return pd.DataFrame(ws.get_all_records())

df = load_df()
today = datetime.now(TZ).strftime("%Y-%m-%d")

# ==============================
# CEK ABSEN DOBEL
# ==============================
def sudah_absen(nama):
    if df.empty:
        return False
    return not df[
        (df["Nama Guru"] == nama) &
        (df["Tanggal"] == today)
    ].empty

# ==============================
# AMBIL LOKASI GPS
# ==============================
st.markdown("""
<script>
navigator.geolocation.getCurrentPosition(
    (pos) => {
        document.getElementById("lat").value = pos.coords.latitude;
        document.getElementById("lon").value = pos.coords.longitude;
    }
);
</script>
""", unsafe_allow_html=True)

lat = st.text_input("Latitude", key="lat")
lon = st.text_input("Longitude", key="lon")

# ==============================
# FORM ABSENSI
# ==============================
with st.form("absen"):
    nama = st.selectbox("Nama Guru", GURU_LIST)
    submit = st.form_submit_button("✅ Absen Sekarang")

# ==============================
# PROSES ABSEN
# ==============================
if submit:

    if sudah_absen(nama):
        st.error("❌ Anda sudah absen hari ini")
        st.stop()

    if lat == "" or lon == "":
        st.error("❌ Lokasi belum terbaca. Aktifkan GPS.")
        st.stop()

    now = datetime.now(TZ)
    jam = now.strftime("%H:%M:%S")
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"

    no = len(df) + 1

    ws.append_row([
        no,
        today,
        nama,
        jam,
        lat,
        lon,
        maps_link
    ])

    st.success("✅ Absensi berhasil")
    st.markdown(f"📍 [Lihat Lokasi di Google Maps]({maps_link})")

# ==============================
# ADMIN REKAP
# ==============================
st.divider()
st.subheader("🔐 Rekap Admin")

password = st.text_input("Password Admin", type="password")

if password == "bkq2025":
    st.dataframe(load_df(), use_container_width=True)
