import streamlit as st
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# ---------------------------
# SECRETS
# ---------------------------
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL")
GOOGLE_SERVICE_ACCOUNT = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")

if not SPREADSHEET_URL or not GOOGLE_SERVICE_ACCOUNT:
    st.error("❌ Secrets belum lengkap. Pastikan SPREADSHEET_URL dan GOOGLE_SERVICE_ACCOUNT sudah diisi di Streamlit Secrets.")
    st.stop()

# ---------------------------
# GOOGLE SHEETS AUTH
# ---------------------------
try:
    credentials_dict = json.loads(GOOGLE_SERVICE_ACCOUNT)
    scopes = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scopes)
    gc = gspread.authorize(creds)
except Exception as e:
    st.error(f"Gagal membaca GOOGLE_SERVICE_ACCOUNT.\nDetail: {e}")
    st.stop()

# ---------------------------
# BUKA SPREADSHEET
# ---------------------------
try:
    sh = gc.open_by_url(SPREADSHEET_URL)
except Exception as e:
    st.error(f"Gagal membuka spreadsheet.\nDetail: {e}")
    st.stop()

SHEET_TITLE = "Absensi"
try:
    worksheet = sh.worksheet(SHEET_TITLE)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_TITLE, rows="2000", cols="20")
    header = ["Tanggal","Nama Guru","Status","Jam Masuk","Denda","Keterangan"]
    worksheet.append_row(header)

# ---------------------------
# LIST GURU
# ---------------------------
guru_list = ["Yolan","Husnia","Rima","Rifa","Sela","Ustadz A","Ustadz B","Ustadz C"]

# ---------------------------
# HELPERS
# ---------------------------
@st.cache_data(ttl=20)
def load_sheet_df():
    records = worksheet.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=["Tanggal","Nama Guru","Status","Jam Masuk","Denda","Keterangan"])

def append_absen_row(row):
    worksheet.append_row(row)
    load_sheet_df.clear()

def hitung_denda(nama, jam_masuk, status):
    if status != "Hadir":
        return 4000
    piket = ["Ustadz A","Ustadz B","Ustadz C"]
    batas = dt_time(7,0) if nama in piket else dt_time(7,10)
    jam = datetime.strptime(jam_masuk,"%H:%M:%S").time()
    if jam > batas:
        return 2000
    return 0

def create_pdf(df, title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    elements.append(Spacer(1,12))
    if df.empty:
        elements.append(Paragraph("Tidak ada data.", styles['Normal']))
    else:
        data = [df.columns.tolist()] + df.astype(str).values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.lightblue),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')
        ]))
        elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---------------------------
# HEADER
# ---------------------------
st.image("https://upload.wikimedia.org/wikipedia/commons/4/4a/Logo_Pendidikan_Indonesia.png", width=90)
st.title("📘 Absensi Guru SD Tahfidz BKQ")

# ---------------------------
# MENU
# ---------------------------
menu = st.sidebar.radio("📋 Menu", ["Absensi","Rekap"])

# ---------------------------
# ABSENSI PAGE REAL-TIME
# ---------------------------
if menu == "Absensi":
    tz = ZoneInfo("Asia/Jakarta")
    placeholder_time = st.empty()
    placeholder_rekap = st.empty()

    with st.form("form_absen", clear_on_submit=True):
        nama_guru = st.selectbox("Nama Guru", guru_list)
        status_manual = st.selectbox("Status", ["Hadir","Izin","Cuti","Tidak Hadir"])
        keterangan = st.text_input("Keterangan (opsional)")
        submitted = st.form_submit_button("✨ Absen Sekarang", type="primary")
        if submitted:
            jam_masuk = datetime.now(tz).strftime("%H:%M:%S")
            denda = hitung_denda(nama_guru, jam_masuk, status_manual)
            row = [datetime.now(tz).strftime("%Y-%m-%d"), nama_guru, status_manual, jam_masuk, denda, keterangan]
            append_absen_row(row)
            st.success(f"🎆 Absen berhasil! Denda: Rp{denda}")

    # Loop real-time update
    import threading
    import time as t

    def update_time_and_rekap():
        while True:
            now = datetime.now(tz)
            placeholder_time.markdown(f"**Tanggal:** {now.strftime('%A, %d %B %Y')}  \n⏰ **Waktu:** {now.strftime('%H:%M:%S')}")
            # Rekapan kehadiran hari ini
            df = load_sheet_df()
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
            df_hari_ini = df[df['Tanggal'].dt.date == now.date()]
            if not df_hari_ini.empty:
                placeholder_rekap.dataframe(df_hari_ini[["Nama Guru","Status","Jam Masuk","Denda","Keterangan"]])
            t.sleep(1)

    threading.Thread(target=update_time_and_rekap, daemon=True).start()

# ---------------------------
# REKAP PAGE
# ---------------------------
elif menu == "Rekap":
    st.header("📑 Rekap Data Absensi Guru")
    df = load_sheet_df()
    if df.empty:
        st.info("Belum ada data absensi.")
        st.stop()

    df['Tanggal'] = pd.to_datetime(df['Tanggal'])
    df['Bulan'] = df['Tanggal'].dt.to_period('M').astype(str)
    tab1, tab2, tab3 = st.tabs(["📅 Harian","📆 Bulanan","👤 Per Guru"])

    with tab1:
        harian = df.groupby("Tanggal").size().reset_index(name="Jumlah Kehadiran")
        st.dataframe(harian)
        pdf_buffer = create_pdf(harian, "Rekap Harian Absensi Guru")
        st.download_button("📄 Unduh PDF Rekap Harian", pdf_buffer, "rekap_harian.pdf", "application/pdf")
