import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import json
from google.oauth2.service_account import Credentials
import gspread
from PIL import Image, ImageDraw

# =====================================================
# KONFIGURASI HALAMAN
# =====================================================
st.set_page_config(
    page_title="Absensi Guru SD Tahfidz BKQ",
    layout="centered"
)

st.title("📸 Absensi Guru SD Tahfidz BKQ")
st.caption("Selfie langsung + lokasi GPS")

# =====================================================
# GOOGLE SHEETS AUTH
# =====================================================
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
    ws = sh.add_worksheet(title="Absensi", rows="2000", cols="15")
    ws.append_row([
        "No","Tanggal","Nama Guru","Jam Masuk",
        "Latitude","Longitude","Link Maps","Keterangan"
    ])

# =====================================================
# DATA GURU
# =====================================================
GURU_LIST = [
    "Yolan","Husnia","Rima","Rifa",
    "Sela","Ustadz A","Ustadz B","Ustadz C"
]

TZ = pytz.timezone("Asia/Jakarta")
today = datetime.now(TZ).strftime("%Y-%m-%d")

# =====================================================
# LOAD DATA
# =====================================================
def load_df():
    data = ws.get_all_records()
    return pd.DataFrame(data)

df = load_df()

# =====================================================
# CEK ABSEN DOBEL
# =====================================================
def sudah_absen(nama):
    if df.empty:
        return False
    cek = df[
        (df["Nama Guru"] == nama) &
        (df["Tanggal"] == today)
    ]
    return not cek.empty

# =====================================================
# AMBIL LOKASI GPS (HTML)
# =====================================================
st.markdown("""
<script>
function getLocation() {
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      document.getElementById("lat").value = pos.coords.latitude;
      document.getElementById("lon").value = pos.coords.longitude;
    }
  );
}
getLocation();
</script>
""", unsafe_allow_html=True)

lat = st.text_input("Latitude", key="lat")
lon = st.text_input("Longitude", key="lon")

# =====================================================
# FORM ABSENSI
# =====================================================
with st.form("form_absensi"):
    nama = st.selectbox("Nama Guru", GURU_LIST)
    selfie = st.camera_input("📷 Ambil Selfie SekARANG")
    submit = st.form_submit_button("✅ Absen Sekarang")

# =====================================================
# PROSES ABSENSI
# =====================================================
if submit:

    if sudah_absen(nama):
        st.error("❌ Anda sudah absen hari ini")
        st.stop()

    if selfie is None:
        st.error("❌ Selfie wajib diambil")
        st.stop()

    if lat == "" or lon == "":
        st.error("❌ Lokasi GPS tidak terbaca")
        st.stop()

    # Timestamp
    now = datetime.now(TZ)
    jam = now.strftime("%H:%M:%S")

    # Link Google Maps
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"

    # Watermark foto
    img = Image.open(selfie).convert("RGB")
    draw = ImageDraw.Draw(img)
    watermark = f"{nama} | {today} {jam} WIB"
    draw.rectangle((5, img.height-35, 450, img.height), fill=(0,0,0))
    draw.text((10, img.height-30), watermark, fill="white")

    # Simpan sementara (lokal container)
    filename = f"selfie_{nama}_{today}_{jam}.jpg"
    img.save(filename)

    # Nomor urut
    no = len(df) + 1

    # Simpan ke Sheets
    ws.append_row([
        no,
        today,
        nama,
        jam,
        lat,
        lon,
        maps_link,
        "Selfie + Lokasi"
    ])

    st.success("✅ Absensi berhasil disimpan")
    st.image(img, caption="Selfie Tersimpan")
    st.markdown(f"📍 [Lihat Lokasi di Google Maps]({maps_link})")

# =====================================================
# ADMIN REKAP
# =====================================================
st.divider()
st.subheader("🔐 Rekap Admin")

password = st.text_input("Password Admin", type="password")

if password == "bkq2025":
    df = load_df()
    st.dataframe(df, use_container_width=True)
