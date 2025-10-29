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
import time
import pytz

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
    return 2000 if jam > batas else 0

def create_pdf(df, title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"<b>{title}</b>", styles['Title']), Spacer(1,12)]
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

def play_fireworks():
    html = """<div style='position:fixed; top:0; left:0; width:100%; height:100%; z-index:9999; pointer-events:none;'>
        <canvas id='fireworks'></canvas></div>
        <script>
        const canvas=document.getElementById('fireworks');
        const ctx=canvas.getContext('2d');
        canvas.width=window.innerWidth;
        canvas.height=window.innerHeight;
        const fireworks=[];
        function random(min,max){return Math.random()*(max-min)+min;}
        function Firework(x,y){this.x=x;this.y=y;this.color=`hsl(${Math.floor(Math.random()*360)},100%,60%)`;this.radius=random(2,4);this.alpha=1;this.vx=random(-5,5);this.vy=random(-5,5);}
        Firework.prototype.update=function(){this.x+=this.vx;this.y+=this.vy;this.alpha-=0.02;}
        function animate(){ctx.clearRect(0,0,canvas.width,canvas.height);for(let i=0;i<fireworks.length;i++){const f=fireworks[i];ctx.beginPath();ctx.arc(f.x,f.y,f.radius,0,2*Math.PI);ctx.fillStyle=f.color;ctx.globalAlpha=f.alpha;ctx.fill();f.update();}requestAnimationFrame(animate);}
        for(let i=0;i<100;i++){fireworks.push(new Firework(window.innerWidth/2,window.innerHeight/2));}
        animate();</script>"""
    st.markdown(html, unsafe_allow_html=True)

# ---------------------------
# HEADER
# ---------------------------
st.image("https://raw.githubusercontent.com/proyekabsen1-dotcom/absensiguru/main/1749893097089.png", width=90)
st.title("📘 Absensi Guru SD Tahfidz BKQ")

# ---------------------------
# MENU
# ---------------------------
menu = st.sidebar.radio("📋 Menu", ["Absensi","Rekap"])

# ---------------------------
# ABSENSI PAGE
# ---------------------------
if menu == "Absensi":
    tz = pytz.timezone("Asia/Jakarta")
    placeholder = st.empty()
    st.subheader("Input Absensi")

    with st.form("form_absen", clear_on_submit=True):
        nama_guru = st.selectbox("Nama Guru", guru_list)
        status_manual = st.selectbox("Status", ["Hadir","Izin","Cuti","Tidak Hadir"])
        keterangan = st.text_input("Keterangan (opsional)")
        submitted = st.form_submit_button("✨ Absen Sekarang", type="primary")
        if submitted:
            now = datetime.now(tz)
            jam_masuk = now.strftime("%H:%M:%S")
            denda = hitung_denda(nama_guru, jam_masuk, status_manual)
            row = [now.strftime("%Y-%m-%d"), nama_guru, status_manual, jam_masuk, denda, keterangan]
            append_absen_row(row)
            play_fireworks()
            st.success(f"🎆 Absen berhasil! Denda: Rp{denda}")

    for _ in range(10):
        now = datetime.now(tz)
        placeholder.markdown(f"**Tanggal:** {now.strftime('%A, %d %B %Y')}  \n⏰ **Waktu (WIB):** {now.strftime('%H:%M:%S')}")
        time.sleep(1)

    df_today = load_sheet_df()
    if not df_today.empty:
        df_today['Tanggal'] = pd.to_datetime(df_today['Tanggal'])
        hari_ini = df_today[df_today['Tanggal'].dt.date == datetime.now(tz).date()]
        if not hari_ini.empty:
            st.subheader("✅ Guru yang sudah absen hari ini")
            hari_ini_display = hari_ini.reset_index(drop=True)
            hari_ini_display.index += 1
            hari_ini_display = hari_ini_display.rename(columns={
                "Jam Masuk": "Jam Kedatangan",
                "Nama Guru": "Nama Guru",
                "Status": "Kehadiran",
                "Denda": "Keterangan Denda"
            })
            st.dataframe(hari_ini_display[["Jam Kedatangan","Nama Guru","Kehadiran","Keterangan Denda","Keterangan"]])

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

    # Rekap Harian
    with tab1:
        st.subheader("Rekap Harian Lengkap")
        df_harian = df.copy()
        df_harian = df_harian.reset_index(drop=True)
        df_harian.index += 1
        st.dataframe(df_harian[["Tanggal","Jam Masuk","Nama Guru","Status","Denda","Keterangan"]])

    # Rekap Bulanan
    with tab2:
        bulan_pilih = st.selectbox("Pilih Bulan", sorted(df["Bulan"].unique()))
        df_bulan = df[df["Bulan"] == bulan_pilih]
        if not df_bulan.empty:
            rekap = df_bulan.groupby("Nama Guru").agg(
                Hadir=('Status', lambda x: (x=='Hadir').sum()),
                Izin=('Status', lambda x: (x=='Izin').sum()),
                Cuti=('Status', lambda x: (x=='Cuti').sum()),
                TidakHadir=('Status', lambda x: (x=='Tidak Hadir').sum()),
                TotalDenda=('Denda', 'sum')
            ).reset_index()
            rekap.index += 1
            st.dataframe(rekap)
            pdf_buffer = create_pdf(rekap, f"Rekap Bulanan - {bulan_pilih}")
            st.download_button("📄 Unduh PDF Rekap Bulanan", pdf_buffer, f"rekap_bulanan_{bulan_pilih}.pdf", "application/pdf")

    # Rekap Per Guru
    with tab3:
        guru_pilih = st.selectbox("Pilih Guru", guru_list)
        bulan_guru = st.selectbox("Pilih Bulan (Per Guru)", sorted(df["Bulan"].unique()))
        df_guru = df[(df["Nama Guru"]==guru_pilih) & (df["Bulan"]==bulan_guru)]
        if not df_guru.empty:
            df_guru = df_guru.reset_index(drop=True)
            df_guru.index += 1
            st.dataframe(df_guru[["Tanggal","Nama Guru","Status","Denda","Keterangan"]])
            pdf_buffer = create_pdf(df_guru, f"Rekap {guru_pilih} - {bulan_guru}")
            st.download_button("📄 Unduh PDF Rekap Per Guru", pdf_buffer, f"rekap_{guru_pilih}_{bulan_guru}.pdf", "application/pdf")
