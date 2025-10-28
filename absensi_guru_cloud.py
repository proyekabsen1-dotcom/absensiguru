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
    """Hitung denda berdasarkan jam kedatangan"""
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
    import streamlit as st
    import pandas as pd
    from datetime import datetime
    import time

    header_placeholder = st.empty()
    table_placeholder = st.empty()
    
    def update_header():
        now = datetime.now()
        header_placeholder.markdown(f"**Tanggal:** {now.strftime('%A, %d %B %Y')}  \n⏰ **Waktu:** {now.strftime('%H:%M:%S')}")

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

    # ---------------------------
    # TAMPILKAN REKAP HARI INI REAL-TIME DENGAN HIGHLIGHT
    # ---------------------------
    update_header()
    df = load_sheet_df()
    today_str = datetime.now().strftime("%Y-%m-%d")
    hari_ini = df[df['Tanggal'] == today_str]

    if not hari_ini.empty:
        # Tabel detail
        table_placeholder.subheader("📋 Rekapan Kehadiran Hari Ini")
        styled_table = hari_ini.style.apply(lambda x: ['background-color: lightgreen' if x.name == len(hari_ini)-1 else '' for i in x], axis=1)
        table_placeholder.dataframe(styled_table)

        # Ringkasan per guru
        ringkasan = hari_ini.groupby("Nama Guru").agg(
            Jumlah_Hadir=("Status", lambda x: (x=="Hadir").sum()),
            Total_Denda=("Denda", "sum")
        ).reset_index()
        table_placeholder.subheader("📊 Ringkasan Kehadiran & Denda")
        table_placeholder.dataframe(ringkasan)

        # Tombol unduh PDF
        pdf_buffer = create_pdf_harian(hari_ini, ringkasan)
        st.download_button("📄 Unduh PDF Rekap Hari Ini", pdf_buffer, "rekap_hari_ini.pdf", "application/pdf")

def create_pdf_harian(df_detail, df_ringkasan):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Judul
    elements.append(Paragraph("<b>Rekap Absensi Hari Ini</b>", styles['Title']))
    elements.append(Spacer(1,12))

    # Tabel Detail
    elements.append(Paragraph("<b>📋 Detail Kehadiran</b>", styles['Heading2']))
    if df_detail.empty:
        elements.append(Paragraph("Tidak ada data.", styles['Normal']))
    else:
        data = [df_detail.columns.tolist()] + df_detail.astype(str).values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.lightblue),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')
        ]))
        elements.append(table)
    elements.append(Spacer(1,12))

    # Tabel Ringkasan
    elements.append(Paragraph("<b>📊 Ringkasan Per Guru</b>", styles['Heading2']))
    if df_ringkasan.empty:
        elements.append(Paragraph("Tidak ada data.", styles['Normal']))
    else:
        data_sum = [df_ringkasan.columns.tolist()] + df_ringkasan.astype(str).values.tolist()
        table_sum = Table(data_sum)
        table_sum.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.lightgreen),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')
        ]))
        elements.append(table_sum)

    doc.build(elements)
    buffer.seek(0)
    return buffer

