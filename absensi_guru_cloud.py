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
from PIL import Image, ImageDraw, ImageFont
import hashlib


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
    header = ["No", "Tanggal","Nama Guru","Status","Jam Masuk","Denda","Keterangan"]
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
    df = pd.DataFrame(records)
    if not df.empty:
        df.columns = df.columns.str.strip().str.title()
        if 'No' not in df.columns or df['No'].isnull().all():
            df.insert(0, 'No', range(1, len(df)+1))
    return df

def append_absen_row(row):
    df_existing = load_sheet_df()
    no = len(df_existing) + 1
    worksheet.append_row([no] + row)
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

def buat_nomor_urut(df):
    df = df.copy()
    if 'No' in df.columns:
        df.drop(columns=['No'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(1, 'No', range(1, len(df) + 1))
    return df

def generate_qr_token():
    today = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d")
    secret = "BKQ-ABSENSI-2025"  # boleh diganti
    token = hashlib.sha256(f"{today}-{secret}".encode()).hexdigest()[:8]
    return token

def add_watermark(image_file, nama_guru):
    img = Image.open(image_file).convert("RGB")
    draw = ImageDraw.Draw(img)

    now = datetime.now(pytz.timezone("Asia/Jakarta"))
    watermark_text = f"{nama_guru} | {now.strftime('%d-%m-%Y %H:%M:%S')} WIB"

    width, height = img.size
    x, y = 10, height - 30

    draw.rectangle((x-5, y-5, x+450, y+20), fill=(0,0,0))
    draw.text((x, y), watermark_text, fill="white")

    return img



# ---------------------------
# HEADER
# ---------------------------
try:
    st.image("https://raw.githubusercontent.com/proyekabsen1-dotcom/absensiguru/main/1749893097089.png", width=90)
except:
    st.markdown("### 🏫 SD Tahfidz BKQ")

st.title("📘 Absensi Guru SD Tahfidz BKQ")

# ---------------------------
# MENU
# ---------------------------
menu = st.sidebar.radio("📋 Menu", ["Absensi","Rekap"])

# ---------------------------
# ABSENSI PAGE
# ---------------------------
if menu == "Absensi":
    st.subheader("📸 Absensi QR + Selfie")

    qr_token_hari_ini = generate_qr_token()

    with st.form("form_absen_qr"):
        nama_guru = st.selectbox("Nama Guru", guru_list)
        input_qr = st.text_input("Masukkan Kode QR Hari Ini")
        foto = st.camera_input("Ambil Foto Selfie Sekarang")

        submit = st.form_submit_button("✅ Absen Sekarang")

        if submit:
            if input_qr != qr_token_hari_ini:
                st.error("❌ QR tidak valid / bukan QR hari ini")
                st.stop()

            if foto is None:
                st.error("❌ Foto selfie wajib diambil")
                st.stop()

            foto_watermark = add_watermark(foto, nama_guru)

            foto_name = f"selfie_{nama_guru}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            foto_watermark.save(foto_name)

            now = datetime.now(pytz.timezone("Asia/Jakarta"))
            jam_masuk = now.strftime("%H:%M:%S")
            denda = hitung_denda(nama_guru, jam_masuk, "Hadir")

            row = [
                now.strftime("%Y-%m-%d"),
                nama_guru,
                "Hadir",
                jam_masuk,
                denda,
                "QR + Selfie"
            ]

            append_absen_row(row)

            st.success("✅ Absensi berhasil")
            st.image(foto_watermark, caption="Foto Selfie Tersimpan")

    # ===== ABSENSI MANUAL (OPSIONAL) =====
    tz = pytz.timezone("Asia/Jakarta")
    placeholder = st.empty()

    st.subheader("Input Absensi Manual")
    with st.form("form_absen", clear_on_submit=True):
        nama_guru = st.selectbox("Nama Guru", guru_list, key="manual")
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


# ---------------------------
# REKAP PAGE
# ---------------------------
elif menu == "Rekap":

    # ===== AUTH ADMIN =====
    password = st.sidebar.text_input("Masukkan Kode Admin", type="password")
    if password != "bkq2025":
        st.warning("Masukkan kode admin untuk melihat rekap.")
        st.stop()

    st.header("📑 Rekap Data Absensi Guru")

    # ===== LOAD DATA =====
    df = load_sheet_df()
    if df.empty:
        st.info("Belum ada data absensi.")
        st.stop()

    # ===== VALIDASI TANGGAL =====
    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df = df[df['Tanggal'].notna()]

    # ===== MENU REKAP =====
    menu_rekap = st.selectbox(
        "Pilih Jenis Rekap",
        ["📅 Harian", "📆 Bulanan", "👤 Per Guru"]
    )

    st.divider()

    # ======================================================
    # 📅 REKAP HARIAN
    # ======================================================
    if menu_rekap == "📅 Harian":

        tgl_pilih = st.date_input(
            "Pilih Tanggal",
            datetime.now().date()
        )

        df_harian = df[df['Tanggal'].dt.date == tgl_pilih]

        if not df_harian.empty:
            df_harian = buat_nomor_urut(df_harian)

            st.dataframe(
                df_harian[['No','Jam Masuk','Nama Guru','Status','Denda','Keterangan']],
                use_container_width=True
            )

            total_denda = df_harian['Denda'].sum()
            st.markdown(f"💰 **Total Denda:** Rp{total_denda:,}")

            pdf_buffer = create_pdf(df_harian, f"Rekap Absensi {tgl_pilih}")
            st.download_button(
                "📄 Unduh PDF Rekap Harian",
                pdf_buffer,
                "rekap_harian.pdf",
                "application/pdf"
            )
        else:
            st.info("Tidak ada data pada tanggal ini.")

    # ======================================================
    # 📆 REKAP BULANAN
    # ======================================================
    elif menu_rekap == "📆 Bulanan":

        bulan_list = sorted(
            df['Tanggal'].dt.to_period('M').astype(str).unique()
        )

        if not bulan_list:
            st.info("Data bulanan belum tersedia.")
            st.stop()

        bulan_pilih = st.selectbox(
            "Pilih Bulan",
            bulan_list,
            index=len(bulan_list) - 1
        )

        df_bulan = df[
            df['Tanggal'].dt.to_period('M').astype(str) == bulan_pilih
        ]

        if not df_bulan.empty:
            df_bulan = buat_nomor_urut(df_bulan)

            st.dataframe(
                df_bulan[['No','Tanggal','Jam Masuk','Nama Guru','Status','Denda','Keterangan']],
                use_container_width=True
            )

            total_denda = df_bulan['Denda'].sum()
            st.markdown(f"💰 **Total Denda Bulan {bulan_pilih}:** Rp{total_denda:,}")

            pdf_buffer = create_pdf(df_bulan, f"Rekap Bulanan {bulan_pilih}")
            st.download_button(
                "📄 Unduh PDF Rekap Bulanan",
                pdf_buffer,
                f"rekap_bulanan_{bulan_pilih}.pdf",
                "application/pdf"
            )
        else:
            st.info("Tidak ada data pada bulan ini.")

    # ======================================================
    # 👤 REKAP PER GURU
    # ======================================================
    elif menu_rekap == "👤 Per Guru":

        st.subheader("👤 Rekap Absensi Per Guru")

        daftar_guru = sorted(df['Nama Guru'].unique())

        if not daftar_guru:
            st.info("Data guru belum tersedia.")
            st.stop()

        guru_pilih = st.selectbox(
            "Pilih Guru",
            daftar_guru,
            key="guru_rekap"
        )

        df_guru = df[df['Nama Guru'] == guru_pilih]

        if not df_guru.empty:
            df_guru = buat_nomor_urut(df_guru)

            st.dataframe(
                df_guru[['No','Tanggal','Jam Masuk','Status','Denda','Keterangan']],
                use_container_width=True
            )

            total_denda = df_guru['Denda'].sum()
            st.markdown(f"💰 **Total Denda {guru_pilih}:** Rp{total_denda:,}")

            pdf_buffer = create_pdf(df_guru, f"Rekap Absensi {guru_pilih}")
            st.download_button(
                "📄 Unduh PDF Rekap Guru",
                pdf_buffer,
                f"rekap_{guru_pilih}.pdf",
                "application/pdf"
            )
        else:
            st.info(f"Tidak ada data untuk {guru_pilih}.")














