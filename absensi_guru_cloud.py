import streamlit as st
from datetime import datetime, time as dt_time
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import pytz
from PIL import Image, ImageDraw
import hashlib


st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# =========================
# SECRETS
# =========================
SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]
GOOGLE_SERVICE_ACCOUNT = st.secrets["GOOGLE_SERVICE_ACCOUNT"]

# =========================
# GOOGLE SHEET
# =========================
credentials_dict = json.loads(GOOGLE_SERVICE_ACCOUNT)
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scopes)
gc = gspread.authorize(creds)
sh = gc.open_by_url(SPREADSHEET_URL)

try:
    worksheet = sh.worksheet("Absensi")
except:
    worksheet = sh.add_worksheet("Absensi", rows="2000", cols="20")
    worksheet.append_row(
        ["No", "Tanggal", "Nama Guru", "Status", "Jam Masuk", "Denda", "Keterangan"]
    )

guru_list = ["Yolan", "Husnia", "Rima", "Rifa", "Sela", "Ustadz A", "Ustadz B", "Ustadz C"]

# =========================
# FUNCTIONS
# =========================
@st.cache_data(ttl=30)
def load_sheet_df():
    df = pd.DataFrame(worksheet.get_all_records())
    return df

def append_absen(row):
    df = load_sheet_df()
    no = len(df) + 1
    worksheet.append_row([no] + row)
    load_sheet_df.clear()

def hitung_denda(nama, jam, status):
    if status != "Hadir":
        return 4000
    batas = dt_time(7, 0) if nama.startswith("Ustadz") else dt_time(7, 10)
    return 2000 if datetime.strptime(jam, "%H:%M:%S").time() > batas else 0

def generate_qr_token():
    today = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d")
    secret = "BKQ-ABSENSI-2025"
    return hashlib.sha256(f"{today}-{secret}".encode()).hexdigest()[:8]

def add_watermark(image_file, nama_guru):
    img = Image.open(image_file).convert("RGB")
    draw = ImageDraw.Draw(img)

    now = datetime.now(pytz.timezone("Asia/Jakarta"))
    text = f"{nama_guru} | {now.strftime('%d-%m-%Y %H:%M:%S')} WIB"

    w, h = img.size
    x, y = 10, h - 35

    draw.rectangle((x-5, y-5, x+500, y+25), fill=(0,0,0))
    draw.text((x, y), text, fill="white")

    return img


def buat_nomor_urut(df):
    df = df.reset_index(drop=True)
    df.insert(0, "No", range(1, len(df) + 1))
    return df

def create_pdf(df, title):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Spacer(1, 12)
    ]
    table = Table([df.columns.tolist()] + df.astype(str).values.tolist())
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue)
    ]))
    elements.append(table)
    doc.build(elements)
    buf.seek(0)
    return buf

def get_location():
    return st.components.v1.html(
        """
        <script>
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                document.getElementById("lat").value = pos.coords.latitude;
                document.getElementById("lon").value = pos.coords.longitude;
            }
        );
        </script>
        <input id="lat" value="" />
        <input id="lon" value="" />
        """,
        height=0
    )


# =========================
# HEADER
# =========================
st.title("📘 Absensi Guru SD Tahfidz BKQ")

menu = st.sidebar.radio("Menu", ["Absensi", "Rekap"])

# =========================
# ABSENSI
# =========================
# ---------------------------
# ABSENSI PAGE (FINAL STABIL)
# ---------------------------
if menu == "Absensi":

    st.subheader("📸 Absensi Guru (Selfie Wajib)")

    st.info("""
    ✅ Foto diambil langsung dari kamera  
    ✅ Ada watermark waktu  
    ❌ Tidak bisa upload foto lama  
    """)

    with st.form("form_absensi_selfie"):
        nama_guru = st.selectbox("Nama Guru", guru_list)
        foto = st.camera_input("Ambil Foto Sekarang")

        submit = st.form_submit_button("✅ Absen Sekarang")

        if submit:

            if foto is None:
                st.error("❌ Foto selfie WAJIB diambil")
                st.stop()

            # Watermark foto
            foto_fix = add_watermark(foto, nama_guru)

            # Waktu
            now = datetime.now(pytz.timezone("Asia/Jakarta"))
            jam_masuk = now.strftime("%H:%M:%S")

            # Hitung denda
            denda = hitung_denda(nama_guru, jam_masuk, "Hadir")

            # Simpan foto (opsional)
            filename = f"selfie_{nama_guru}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
            foto_fix.save(filename)

            # Simpan ke Google Sheet
            append_absen_row([
                now.strftime("%Y-%m-%d"),
                nama_guru,
                "Hadir",
                jam_masuk,
                denda,
                "Selfie Kamera"
            ])

            st.success("✅ Absensi berhasil")
            st.image(foto_fix, caption="Bukti Absensi")




# =========================
# REKAP
# =========================
else:
    if st.sidebar.text_input("Kode Admin", type="password") != "bkq2025":
        st.stop()

    df = load_sheet_df()
    df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce")
    df = df.dropna(subset=["Tanggal"])

    jenis = st.selectbox("Jenis Rekap", ["Harian", "Bulanan", "Per Guru"])

    if jenis == "Harian":
        tgl = st.date_input("Tanggal")
        data = df[df["Tanggal"].dt.date == tgl]

    elif jenis == "Bulanan":
        bulan = st.selectbox("Bulan", df["Tanggal"].dt.to_period("M").astype(str).unique())
        data = df[df["Tanggal"].dt.to_period("M").astype(str) == bulan]

    else:
        guru = st.selectbox("Guru", df["Nama Guru"].unique())
        data = df[df["Nama Guru"] == guru]

    if not data.empty:
        data = buat_nomor_urut(data)
        st.dataframe(data, use_container_width=True)
        st.download_button(
            "📄 Download PDF",
            create_pdf(data, "Rekap Absensi"),
            "rekap.pdf",
            "application/pdf"
        )




