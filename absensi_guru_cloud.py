# absensi_guru_cloud.py
import streamlit as st
from datetime import datetime
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import plotly.express as px
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# ---------------------------
# CONFIG / SECRETS
# ---------------------------
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", None)
GOOGLE_SERVICE_ACCOUNT = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", None)

if SPREADSHEET_URL is None or GOOGLE_SERVICE_ACCOUNT is None:
    st.error("Secrets belum lengkap. Pastikan SPREADSHEET_URL dan GOOGLE_SERVICE_ACCOUNT sudah diisi di Streamlit Secrets.")
    st.stop()

# ---------------------------
# AUTH GOOGLE SHEETS
# ---------------------------
try:
    if isinstance(GOOGLE_SERVICE_ACCOUNT, str):
        credentials_dict = json.loads(GOOGLE_SERVICE_ACCOUNT)
    else:
        credentials_dict = GOOGLE_SERVICE_ACCOUNT

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scopes)
    gc = gspread.authorize(creds)
except Exception as e:
    st.error(f"Gagal membaca GOOGLE_SERVICE_ACCOUNT dari secrets. Pastikan format JSON benar.\n\nDetail error: {e}")
    st.stop()

# ---------------------------
# BUKA SPREADSHEET & WORKSHEET
# ---------------------------
try:
    sh = gc.open_by_url(SPREADSHEET_URL)
except Exception as e:
    st.error("Gagal membuka spreadsheet. Periksa SPREADSHEET_URL dan permission service account.")
    st.stop()

SHEET_TITLE = "Absensi"
try:
    worksheet = sh.worksheet(SHEET_TITLE)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_TITLE, rows="2000", cols="20")
    header = ["Tanggal","Nama Guru","Status","Jam Masuk","Jam Pulang","Denda","Keterangan"]
    worksheet.append_row(header)

# ---------------------------
# LIST GURU
# ---------------------------
guru_list = ["Yolan", "Husnia", "Rima", "Rifa", "Sela", "Ustadz A", "Ustadz B", "Ustadz C"]

# ---------------------------
# HELPERS
# ---------------------------
@st.cache_data(ttl=20)
def load_sheet_df():
    records = worksheet.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=["Tanggal","Nama Guru","Status","Jam Masuk","Jam Pulang","Denda","Keterangan"])

def create_pdf(df, title):
    """Membuat file PDF dari DataFrame"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    if df.empty:
        elements.append(Paragraph("Tidak ada data.", styles['Normal']))
    else:
        data = [df.columns.tolist()] + df.astype(str).values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def play_ding():
    sound_data = "data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAACcQCA"
    st.markdown(f"""<audio autoplay><source src="{sound_data}" type="audio/mp3"></audio>""", unsafe_allow_html=True)

def append_absen_row(row):
    worksheet.append_row(row)
    load_sheet_df.clear()

# ---------------------------
# MENU
# ---------------------------
menu = st.sidebar.radio("📌 Menu", ["Absensi", "Rekap"])

# ---------------------------
# ABSENSI PAGE
# ---------------------------
if menu == "Absensi":
    st.title("📌 Absensi Guru SD Tahfidz BKQ")
    now = datetime.now()
    st.markdown(f"**Tanggal:** {now.strftime('%A, %d %B %Y')} — **Jam:** {now.strftime('%H:%M:%S')}")

    st.subheader("Input Absensi (otomatis 'Hadir' ketika klik tombol)")
    with st.form("form_absen", clear_on_submit=True):
        col1, col2 = st.columns([2,2])
        with col1:
            nama_guru = st.selectbox("Nama Guru", guru_list)
        with col2:
            status_manual = st.selectbox("Ubah status (opsional)", ["Otomatis Hadir", "Izin", "Cuti", "Tidak Hadir"])
        jam_masuk_auto = now.strftime("%H:%M:%S")
        jam_pulang = st.text_input("Jam Pulang (HH:MM)", value="")
        keterangan = st.text_input("Keterangan", value="")

        submitted = st.form_submit_button("✨ Absen Sekarang", type="primary")
        if submitted:
            status_to_save = "Hadir" if status_manual == "Otomatis Hadir" else status_manual
            denda = 2000 if status_to_save.lower().startswith("telat") else 0
            row = [now.strftime("%Y-%m-%d"), nama_guru, status_to_save, jam_masuk_auto if status_to_save=="Hadir" else "", jam_pulang, denda, keterangan]
            append_absen_row(row)
            play_ding()
            st.success(f"✅ {nama_guru} berhasil absen sebagai '{status_to_save}'")
            st.balloons()

# ---------------------------
# REKAP PAGE
# ---------------------------
elif menu == "Rekap":
    st.title("📑 Rekap Data Absensi Guru")
    df = load_sheet_df()
    if df.empty:
        st.info("Belum ada data absensi.")
        st.stop()

    df['Tanggal'] = pd.to_datetime(df['Tanggal'])
    df['Bulan'] = df['Tanggal'].dt.to_period('M').astype(str)
    tab1, tab2, tab3 = st.tabs(["📅 Rekap Harian", "📆 Rekap Bulanan Semua", "👤 Rekap per Guru"])

    # 1️⃣ Rekap Harian
    with tab1:
        harian = df.groupby("Tanggal").size().reset_index(name="Jumlah Kehadiran")
        st.subheader("Rekap Harian")
        st.dataframe(harian)
        pdf_buffer = create_pdf(harian, "Rekap Harian Absensi Guru")
        st.download_button("📄 Unduh PDF Rekap Harian", pdf_buffer, "rekap_harian.pdf", "application/pdf")

    # 2️⃣ Rekap Bulanan
    with tab2:
        bulanan = df.groupby(['Bulan','Nama Guru']).agg(
            Jumlah_Hadir=('Nama Guru','count'),
            Total_Denda=('Denda','sum')
        ).reset_index()
        st.subheader("Rekap Bulanan Semua Guru")
        st.dataframe(bulanan)
        pdf_buffer = create_pdf(bulanan, "Rekap Bulanan Semua Guru")
        st.download_button("📄 Unduh PDF Rekap Bulanan", pdf_buffer, "rekap_bulanan.pdf", "application/pdf")

    # 3️⃣ Rekap per Guru
    with tab3:
        guru_pilih = st.selectbox("Pilih Guru", guru_list)
        periode_mulai = st.date_input("Mulai", value=datetime.now().replace(day=1))
        periode_akhir = st.date_input("Akhir", value=datetime.now())
        dfg = df[(df['Nama Guru'] == guru_pilih) &
                 (df['Tanggal'].dt.date >= periode_mulai) &
                 (df['Tanggal'].dt.date <= periode_akhir)]
        if dfg.empty:
            st.info("Tidak ada data.")
        else:
            st.dataframe(dfg)
            pdf_buffer = create_pdf(dfg, f"Rekap {guru_pilih} ({periode_mulai} - {periode_akhir})")
            st.download_button("📄 Unduh PDF Rekap Guru", pdf_buffer, f"rekap_{guru_pilih}.pdf", "application/pdf")
