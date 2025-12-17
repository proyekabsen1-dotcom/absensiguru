import streamlit as st
import pandas as pd
from datetime import datetime
import pytz, json, math
from PIL import Image, ImageDraw
from io import BytesIO

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= CONFIG =================
LAT_SEKOLAH = -0.9145
LON_SEKOLAH = 100.4583
RADIUS_METER = 100
TZ = pytz.timezone("Asia/Jakarta")

st.set_page_config("Absensi Guru SD Tahfidz BKQ", layout="wide")

# ================= SECRETS =================
SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]
GOOGLE_SERVICE_ACCOUNT = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
DRIVE_FOLDER_ID = st.secrets["DRIVE_FOLDER_ID"]

# ================= GOOGLE AUTH =================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    GOOGLE_SERVICE_ACCOUNT, scope
)
gc = gspread.authorize(creds)
drive = build("drive", "v3", credentials=creds)

# ================= SHEET =================
sh = gc.open_by_url(SPREADSHEET_URL)
try:
    ws = sh.worksheet("Absensi")
except:
    ws = sh.add_worksheet("Absensi", 2000, 15)
    ws.append_row([
        "Tanggal","Nama Guru","Jam","Latitude","Longitude",
        "Jarak (m)","Maps","Status","Foto"
    ])

# ================= DATA =================
guru_list = ["Yolan","Husnia","Rima","Rifa","Sela","Ustadz A","Ustadz B","Ustadz C"]

# ================= FUNCTIONS =================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dl = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return R * (2*math.atan2(math.sqrt(a), math.sqrt(1-a)))

def upload_drive(img, nama):
    folder_name = datetime.now(TZ).strftime("%Y-%m-%d")
    q = f"name='{folder_name}' and '{DRIVE_FOLDER_ID}' in parents"
    res = drive.files().list(q=q).execute().get("files", [])
    if res:
        folder_id = res[0]["id"]
    else:
        folder = drive.files().create(body={
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents":[DRIVE_FOLDER_ID]
        }).execute()
        folder_id = folder["id"]

    buf = BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    media = MediaIoBaseUpload(buf, mimetype="image/jpeg")
    file = drive.files().create(
        body={"name":f"{nama}.jpg","parents":[folder_id]},
        media_body=media,
        fields="id"
    ).execute()

    return f"https://drive.google.com/file/d/{file['id']}"

def sudah_absen(nama, tgl):
    data = ws.get_all_records()
    for d in data:
        if d["Nama Guru"] == nama and d["Tanggal"] == tgl:
            return True
    return False

# ================= UI =================
st.title("📸 Absensi Guru SD Tahfidz BKQ")
st.info("Selfie + Lokasi otomatis | Radius max 100 meter")

st.markdown("""
<script>
navigator.geolocation.getCurrentPosition(
(pos)=>{
document.getElementById("lat").value = pos.coords.latitude;
document.getElementById("lon").value = pos.coords.longitude;
},
()=>alert("Aktifkan GPS!")
);
</script>
<input id="lat" type="hidden">
<input id="lon" type="hidden">
""", unsafe_allow_html=True)

nama = st.selectbox("Nama Guru", guru_list)
foto = st.camera_input("📷 Ambil Selfie Sekarang")

lat = st.text_input("Latitude", key="lat")
lon = st.text_input("Longitude", key="lon")

if st.button("✅ Absen Sekarang"):
    if not foto or not lat or not lon:
        st.error("Foto & lokasi WAJIB")
        st.stop()

    lat, lon = float(lat), float(lon)
    jarak = haversine(lat, lon, LAT_SEKOLAH, LON_SEKOLAH)

    if jarak > RADIUS_METER:
        st.error("❌ Di luar area sekolah")
        st.stop()

    today = datetime.now(TZ).strftime("%Y-%m-%d")
    if sudah_absen(nama, today):
        st.warning("⚠️ Sudah absen hari ini")
        st.stop()

    img = Image.open(foto)
    draw = ImageDraw.Draw(img)
    draw.text((10,10), f"{nama} {today}", fill="white")

    link_foto = upload_drive(img, nama)
    maps = f"https://maps.google.com/?q={lat},{lon}"

    ws.append_row([
        today, nama, datetime.now(TZ).strftime("%H:%M:%S"),
        lat, lon, round(jarak,1), maps, "Hadir", link_foto
    ])

    st.success("✅ Absensi berhasil")
    st.image(img)
    st.markdown(f"[📍 Lihat Lokasi]({maps})")
