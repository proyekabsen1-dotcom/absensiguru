# absensi_guru_cloud.py
import streamlit as st
from datetime import datetime, date, time as dt_time
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import threading
import time

st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# ---------------------------
# CONFIG / SECRETS
# ---------------------------
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", None)
GOOGLE_SERVICE_ACCOUNT = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", None)

if SPREADSHEET_URL is None or GOOGLE_SERVICE_ACCOUNT is None:
    st.error("❌ Secrets belum lengkap. Pastikan SPREADSHEET_URL dan GOOGLE_SERVICE_ACCOUNT sudah diisi di Streamlit Secrets.")
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
    st.error(f"Gagal membaca GOOGLE_SERVICE_ACCOUNT dari secrets.\n\nDetail error: {e}")
    st.stop()

# ---------------------------
# BUKA SPREADSHEET
# ---------------------------
try:
    sh = gc.open_by_url(SPREADSHEET_URL)
except Exception as e:
    st.error(f"Gagal membuka spreadsheet. Pastikan URL benar dan akun service memiliki akses.\n\nDetail: {e}")
    st.stop()

SHEET_TITLE = "Absensi"
try:
    worksheet = sh.worksheet(SHEET_TITLE)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_TITLE, rows="2000", cols="20")
    header = ["Tanggal", "Nama Guru", "Status", "Jam Masuk", "Denda", "Keterangan", "Tipe Guru"]
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
    return pd.DataFrame(records) if records else pd.DataFrame(columns=["Tanggal", "Nama Guru", "Status", "Jam Masuk", "Denda", "Keterangan", "Tipe Guru"])

def append_absen_row(row):
    worksheet.append_row(row)
    load_sheet_df.clear()

def create_pdf(df, title):
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

        style = TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ])
        style.add('BACKGROUND', (0,0), (-1,0), colors.lightblue)

        for i, row in enumerate(data[1:], start=1):
            status = row[df.columns.get_loc('Status')]
            denda = float(row[df.columns.get_loc('Denda')])
            if status.lower() == 'hadir' and denda == 0:
                bg = colors.lightgreen
            elif status.lower() == 'hadir' and denda > 0:
                bg = colors.yellow
            else:
                bg = colors.salmon
            style.add('BACKGROUND', (0,i), (-1,i), bg)

        table.setStyle(style)
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

def play_fireworks():
    fireworks_html = """
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
    function Firework(x,y){
        this.x=x;this.y=y;
        this.color=`hsl(${Math.floor(Math.random()*360)},100%,60%)`;
        this.radius=random(2,4);
        this.alpha=1;
        this.vx=random(-5,5);
        this.vy=random(-5,5);
    }
    Firework.prototype.update=function(){
        this.x+=this.vx;this.y+=this.vy;this.alpha-=0.02;
    }
    function animate(){
        ctx.clearRect(0,0,canvas.width,canvas.height);
        for(let i=0;i<fireworks.length;i++){
            const f=fireworks[i];
            ctx.beginPath();
            ctx.arc(f.x,f.y,f.radius,0,2*Math.PI);
            ctx.fillStyle=f.color;
            ctx.globalAlpha=f.alpha;
            ctx.fill();
            f.update();
        }
        requestAnimationFrame(animate);
    }
    for(let i=0;i<100;i++){fireworks.push(new Firework(window.innerWidth/2,window.innerHeight/2));}
    animate();
    </script>
    """
    st.markdown(fireworks_html, unsafe_allow_html=True)

def color_status(val_status, val_denda):
    if val_status.lower() == 'hadir' and val_denda == 0:
        return 'background-color: lightgreen'
    elif val_status.lower() == 'hadir' and val_denda > 0:
        return 'background-color: yellow'
    else:
        return 'background-color: salmon'

# ---------------------------
# HEADER
# ---------------------------
logo_url = "https://upload.wikimedia.org/wikipedia/commons/4/4a/Logo_Pendidikan_Indonesia.png"
st.image(logo_url, width=90)
st.title("📘 Absensi Guru SD Tahfidz BKQ")

# ---------------------------
# MENU
# ---------------------------
menu = st.sidebar.radio("📋 Menu", ["Absensi", "Rekap"])

# ---------------------------
# ABSENSI PAGE
# ---------------------------
if menu == "Absensi":
    jam_placeholder = st.empty()

    def update_jam_real_time():
        while True:
            now_local = datetime.now()
            jam_placeholder.markdown(
                f"**Tanggal:** {now_local.strftime('%A, %d %B %Y')}  \n⏰ **Waktu:** {now_local.strftime('%H:%M:%S')}"
            )
            time.sleep(1)

    threading.Thread(target=update_jam_real_time, daemon=True).start()

    st.subheader("Input Absensi")
    with st.form("form_absen", clear_on_submit=True):
        nama_guru = st.selectbox("Nama Guru", guru_list)
        tipe_guru = st.selectbox("Tipe Guru", ["Reguler", "Piket"])
        status_manual = st.selectbox("Status", ["Hadir", "Izin", "Cuti", "Tidak Hadir"])
        keterangan = st.text_input("Keterangan (opsional)", "")
        submitted = st.form_submit_button("✨ Absen Sekarang", type="primary")

        if submitted:
            jam_masuk = datetime.now().strftime("%H:%M:%S")
            df_today = load_sheet_df()
            df_today['Tanggal'] = pd.to_datetime(df_today['Tanggal']).dt.date
            if any((df_today['Nama Guru'] == nama_guru) & (df_today['Tanggal'] == datetime.now().date())):
                st.warning(f"⚠️ {nama_guru} sudah absen hari ini.")
            else:
                # Aturan denda
                if status_manual.lower() == 'hadir':
                    if tipe_guru == "Reguler":
                        batas = dt_time(7,10)
                    else:  # Piket
                        batas = dt_time(7,0)
                    masuk_time = datetime.strptime(jam_masuk, "%H:%M:%S").time()
                    denda = 2000 if masuk_time > batas else 0
                else:
                    denda = 4000

                row = [datetime.now().strftime("%Y-%m-%d"), nama_guru, status_manual, jam_masuk, denda, keterangan, tipe_guru]
                append_absen_row(row)
                play_fireworks()
                st.success(f"🎆 Absen hari ini berhasil! Denda: Rp{denda}")

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
    tab1, tab2, tab3 = st.tabs(["📅 Harian", "📆 Bulanan", "👤 Per Guru"])

    # Rekap Harian
    with tab1:
        harian = df.groupby("Tanggal").size().reset_index(name="Jumlah Kehadiran")
        st.dataframe(harian)
        pdf_buffer = create_pdf(harian, "Rekap Harian Absensi Guru")
        st.download_button("📄 Unduh PDF Rekap Harian", pdf_buffer, "rekap_harian.pdf", "application/pdf")

    # Rekap Bulanan
    with tab2:
        bulanan = df.groupby(['Bulan', 'Nama Guru']).agg(Jumlah_Hadir=('Nama Guru', 'count')).reset_index()
        st.dataframe(bulanan)
        pdf_buffer = create_pdf(bulanan, "Rekap Bulanan Semua Guru")
        st.download_button("📄 Unduh PDF Rekap Bulanan", pdf_buffer, "rekap_bulanan.pdf", "application/pdf")

    # Rekap Per Guru dengan tabel berwarna
    with tab3:
        guru_pilih = st.selectbox("Pilih Guru", guru_list)
        dfg = df[df['Nama Guru'] == guru_pilih]
        if not dfg.empty:
            styled_df = dfg.style.apply(
                lambda x: [color_status(x['Status'], float(x['Denda']))]*len(x), axis=1
            )
            st.dataframe(styled_df)
        else:
            st.info("Belum ada data untuk guru ini.")

        pdf_buffer = create_pdf(dfg, f"Rekap {guru_pilih}")
        st.download_button(f"📄 Unduh PDF {guru_pilih}", pdf_buffer, f"rekap_{guru_pilih}.pdf", "application/pdf")
