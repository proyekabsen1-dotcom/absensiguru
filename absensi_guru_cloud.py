import streamlit as st
from datetime import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from io import BytesIO
from PIL import Image, ImageDraw
import pytz
import math

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# =====================================================
# KONFIGURASI
# =====================================================
st.set_page_config("Absensi Guru BKQ", layout="centered")

LAT_SEKOLAH = -0.16861883057236052      # GANTI, 
LON_SEKOLAH = 100.66416954081318    # GANTI
RADIUS_METER = 150

FOLDER_ID_DRIVE = "1K6U3fz6c913a-VlYrFVV13xMvln2z0qr"

GURU_LIST = ["Yolan","Husnia","Rima","Rifa","Sela","Ustadz A","Ustadz B"]

# =====================================================
# AUTH GOOGLE
# =====================================================
credentials_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scopes)
gc = gspread.authorize(creds)

sh = gc.open_by_url(st.secrets["SPREADSHEET_URL"])
try:
    ws = sh.worksheet("Absensi")
except:
    ws = sh.add_worksheet("Absensi", 2000, 10)
    ws.append_row([
        "Tanggal","Nama Guru","Jam","Status","Lokasi (m)","Link Foto","Keterangan"
    ])

# =====================================================
# FUNGSI
# =====================================================
def load_df():
    return pd.DataFrame(ws.get_all_records())

def sudah_absen(nama, tanggal):
    df = load_df()
    if df.empty:
        return False
    df["Tanggal"] = pd.to_datetime(df["Tanggal"])
    return not df[
        (df["Nama Guru"] == nama) &
        (df["Tanggal"].dt.date == tanggal)
    ].empty

def jarak_meter(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def add_watermark(image, nama, jarak):
    img = Image.open(image).convert("RGB")
    draw = ImageDraw.Draw(img)
    now = datetime.now(pytz.timezone("Asia/Jakarta"))
    text = f"{nama} | {now.strftime('%d-%m-%Y %H:%M:%S')} | {int(jarak)} m"
    draw.rectangle((0, img.height-40, img.width, img.height), fill=(0,0,0))
    draw.text((10, img.height-30), text, fill="white")
    return img

def upload_drive(img, filename):
    service = build("drive", "v3", credentials=creds)
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)

    media = MediaIoBaseUpload(buffer, mimetype="image/jpeg")
    file = service.files().create(
        body={"name": filename, "parents":[FOLDER_ID_DRIVE]},
        media_body=media,
        fields="webViewLink"
    ).execute()
    return file["webViewLink"]

# =====================================================
# AMBIL LOKASI (GPS)
# =====================================================
st.markdown("""
<script>
navigator.geolocation.getCurrentPosition(
(pos)=> {
window.location.search='?lat='+pos.coords.latitude+'&lon='+pos.coords.longitude;
});
</script>
""", unsafe_allow_html=True)

lat = st.query_params.get("lat")
lon = st.query_params.get("lon")

# =====================================================
# UI
# =====================================================
st.title("📸 Absensi Guru SD Tahfidz BKQ")

if not lat or not lon:
    st.warning("Menunggu lokasi GPS...")
    st.stop()

jarak = jarak_meter(float(lat), float(lon), LAT_SEKOLAH, LON_SEKOLAH)
if jarak > RADIUS_METER:
    st.error("❌ Anda berada di luar area sekolah")
    st.stop()

nama = st.selectbox("Nama Guru", GURU_LIST)
foto = st.camera_input("Ambil foto selfie (kamera langsung)")

if st.button("✅ Absen Sekarang"):
    now = datetime.now(pytz.timezone("Asia/Jakarta"))

    if sudah_absen(nama, now.date()):
        st.error("❌ Anda sudah absen hari ini")
        st.stop()

    if not foto:
        st.error("❌ Foto wajib")
        st.stop()

    foto_wm = add_watermark(foto, nama, jarak)
    nama_file = f"{nama}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
    link = upload_drive(foto_wm, nama_file)

    ws.append_row([
        now.strftime("%Y-%m-%d"),
        nama,
        now.strftime("%H:%M:%S"),
        "Hadir",
        int(jarak),
        link,
        "Selfie + Lokasi"
    ])

    st.success("✅ Absensi berhasil")
    st.image(foto_wm)


