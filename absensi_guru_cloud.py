import streamlit as st
import pandas as pd
from datetime import datetime, date
import pytz
import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ===============================
# CONFIG
# ===============================
st.set_page_config("Absensi Guru BKQ", layout="wide")
TZ = pytz.timezone("Asia/Jakarta")

SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]
SERVICE_ACCOUNT = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])

TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

GURU_LIST = ["Yolan","Husnia","Rima","Rifa","Sela","Ustadz A","Ustadz B"]

# ===============================
# GOOGLE AUTH
# ===============================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT, scope)
gc = gspread.authorize(creds)
drive = build("drive", "v3", credentials=creds)

sh = gc.open_by_url(SPREADSHEET_URL)
try:
    ws = sh.worksheet("Absensi")
except:
    ws = sh.add_worksheet("Absensi", 2000, 10)
    ws.append_row([
        "Tanggal","Nama Guru","Jam","Lokasi","Foto","Status"
    ])

# ===============================
# HELPERS
# ===============================
@st.cache_data(ttl=30)
def load_df():
    return pd.DataFrame(ws.get_all_records())

def sudah_absen(nama):
    df = load_df()
    hari = datetime.now(TZ).strftime("%Y-%m-%d")
    return not df[
        (df["Nama Guru"]==nama) &
        (df["Tanggal"]==hari)
    ].empty

def kirim_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    })

def upload_drive(img, folder):
    meta = {"name": img.name, "parents":[folder]}
    media = MediaIoBaseUpload(img, mimetype="image/jpeg")
    f = drive.files().create(body=meta, media_body=media).execute()
    return f"https://drive.google.com/file/d/{f['id']}"

def get_folder(tanggal):
    q = f"name='{tanggal}' and mimeType='application/vnd.google-apps.folder'"
    r = drive.files().list(q=q).execute().get("files",[])
    if r: return r[0]["id"]
    f = drive.files().create(body={
        "name": tanggal,
        "mimeType": "application/vnd.google-apps.folder"
    }).execute()
    return f["id"]

def create_pdf(df):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Rekap Absensi Guru", styles["Title"])]
    table = Table([df.columns.tolist()] + df.values.tolist())
    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("BACKGROUND",(0,0),(-1,0),colors.lightgrey)
    ]))
    elements.append(table)
    doc.build(elements)
    buf.seek(0)
    return buf

# ===============================
# UI
# ===============================
st.title("📸 Absensi Guru SD Tahfidz BKQ")

menu = st.sidebar.radio("Menu", ["Absensi","Rekap"])

# ===============================
# ABSENSI
# ===============================
if menu == "Absensi":

    with st.form("absen"):
        nama = st.selectbox("Nama Guru", GURU_LIST)
        lokasi = st.text_input("Lokasi (Google Maps otomatis dari HP)")
        foto = st.camera_input("Ambil Foto Selfie")
        submit = st.form_submit_button("Absen Sekarang")

    if submit:
        if sudah_absen(nama):
            st.error("❌ Anda sudah absen hari ini")
            st.stop()

        if not foto or not lokasi:
            st.error("❌ Foto & lokasi wajib")
            st.stop()

        now = datetime.now(TZ)
        tanggal = now.strftime("%Y-%m-%d")
        jam = now.strftime("%H:%M:%S")

        folder = get_folder(tanggal)
        foto.name = f"{nama}_{jam}.jpg"
        link_foto = upload_drive(foto, folder)

        ws.append_row([
            tanggal, nama, jam, lokasi, link_foto, "Hadir"
        ])

        kirim_telegram(
            f"📌 ABSENSI\n{nama}\n{tanggal} {jam}\n{lokasi}"
        )

        st.success("✅ Absensi berhasil")

# ===============================
# REKAP
# ===============================
else:
    pwd = st.sidebar.text_input("Password Admin", type="password")
    if pwd != "bkq2025":
        st.stop()

    df = load_df()
    st.dataframe(df, use_container_width=True)

    pdf = create_pdf(df)
    st.download_button(
        "📄 Download PDF",
        pdf,
        "rekap_absensi.pdf"
    )
