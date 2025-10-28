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
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# ---------------------------
# SECRETS
# ---------------------------
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL")
GOOGLE_SERVICE_ACCOUNT = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")

if not SPREADSHEET_URL or not GOOGLE_SERVICE_ACCOUNT:
    st.error("❌ Secrets belum lengkap.")
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

def play_fireworks():
    html = """
    <div style='position:fixed; top:0; left:0; width:100%; height:100%; z-index:9999; pointer-events:none;'>
        <canvas id='fireworks'></canvas>
    </div>
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
    animate();
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)

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
        style = TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey),
                            ('BACKGROUND',(0,0),(-1,0),colors.lightblue),
                            ('ALIGN',(0,0),(-1,-1),'CENTER'),
                            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')])
        # Highlight denda >0
        for i, row in enumerate(df.values.tolist(), start=1):
            if int(row[4]) > 0:
                style.add('BACKGROUND', (0,i), (-1,i), colors.lightcoral)
            else:
                style.add('BACKGROUND', (0,i), (-1,i), colors.lightgreen)
        table.setStyle(style)
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
# ABSENSI PAGE
# ---------------------------
if menu == "Absensi":
    st_autorefresh(interval=1000, key="clock")  # update jam real-time
    now = datetime.now()
    st.markdown(f"**Tanggal:** {now.strftime('%A, %d %B %Y')}  \n⏰ **Waktu:** {now.strftime('%H:%M:%S')}")

    st.subheader("Input Absensi")
    with st.form("form_absen", clear_on_submit=True):
        nama_guru = st.selectbox("Nama Guru", guru_list)
        status_manual = st.selectbox("Status", ["Hadir","Izin","Cuti","Tidak Hadir"])
        keterangan = st.text_input("Keterangan (opsional)")
        submitted = st.form_submit_button("✨ Absen Sekarang", type="primary")
        if submitted:
            jam_masuk = datetime.now().strftime("%H:%M:%S")
            denda = hitung_denda(nama_guru, jam_masuk, status_manual)
            row = [datetime.now().strftime("%Y-%m-%d"), nama_guru, status_manual, jam_masuk, denda, keterangan]
            append_absen_row(row)
            play_fireworks()
            st.success(f"🎆 Absen berhasil! Denda: Rp{denda}")

    st.subheader("📄 Rekap Absensi Hari Ini")
    df = load_sheet_df()
    if not df.empty:
        hari_ini = df[df['Tanggal'] == datetime.now().strftime("%Y-%m-%d")]
        if hari_ini.empty:
            st.info("Belum ada guru yang absen hari ini.")
        else:
            def highlight_row(row):
                return ['background-color: lightcoral' if row.Denda>0 else 'background-color: lightgreen']*len(row)
            st.dataframe(hari_ini.style.apply(highlight_row, axis=1))

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

    # Harian
    with tab1:
        harian = df.groupby("Tanggal").size().reset_index(name="Jumlah Kehadiran")
        st.dataframe(harian)
        pdf_buffer = create_pdf(harian, "Rekap Harian Absensi Guru")
        st.download_button("📄 Unduh PDF Rekap Harian", pdf_buffer, "rekap_harian.pdf", "application/pdf")

    # Bulanan
    with tab2:
        bulanan = df.groupby("Bulan").size().reset_index(name="Jumlah Kehadiran")
        st.dataframe(bulanan)
        pdf_buffer = create_pdf(bulanan, "Rekap Bulanan Absensi Guru")
        st.download_button("📄 Unduh PDF Rekap Bulanan", pdf_buffer, "rekap_bulanan.pdf", "application/pdf")

    # Per Guru
    with tab3:
        per_guru = df.groupby("Nama Guru").size().reset_index(name="Jumlah Kehadiran")
        st.dataframe(per_guru)
        pdf_buffer = create_pdf(per_guru, "Rekap Per Guru Absensi")
        st.download_button("📄 Unduh PDF Rekap Per Guru", pdf_buffer, "rekap_per_guru.pdf", "application/pdf")
