import streamlit as st
from datetime import datetime, time
import pandas as pd
from fpdf import FPDF
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import requests
import json
import io

st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# ---------------------------
# Koneksi Google Sheets via Secret
# ---------------------------
scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

service_account_info = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open("Absensi Guru SD Tahfidz BKQ").sheet1

# ---------------------------
# Data Guru
# ---------------------------
guru_list = ["Yolan", "Husnia", "Rima", "Rifa", "Sela", "Ustadz A", "Ustadz B", "Ustadz C"]

# ---------------------------
# Header
# ---------------------------
st.markdown("<h1 style='text-align: center; color: blue;'>📋 Absensi Guru SD Tahfidz BKQ</h1>", unsafe_allow_html=True)
tanggal_sekarang = datetime.now()
st.markdown(f"<p style='text-align: center; font-size:18px;'>🗓 {tanggal_sekarang.strftime('%A, %d %B %Y')}<br>⏰ {tanggal_sekarang.strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

# ---------------------------
# Fungsi Notifikasi Telegram
# ---------------------------
def kirim_telegram(message):
    token = st.secrets["TELEGRAM_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    try:
        requests.get(url)
    except:
        pass

# ---------------------------
# Input Absensi
# ---------------------------
st.subheader("🖊 Input Absensi")
col1, col2 = st.columns([2,1])

with col1:
    nama_guru = st.selectbox("Nama Guru", guru_list)
    status_piket = st.radio("Status Piket", ["Piket", "Tidak Piket"], horizontal=True)

# Hitung denda
jam_piket = time(7, 0)
jam_biasa = time(7, 15)
jam_sekarang = tanggal_sekarang.time()
denda = 0
terlambat = False
if status_piket == "Piket" and jam_sekarang > jam_piket:
    terlambat = True
    denda = 2000
elif status_piket == "Tidak Piket" and jam_sekarang > jam_biasa:
    terlambat = True
    denda = 2000

status_msg = f"{nama_guru} {'TERLAMBAT!' if terlambat else 'hadir tepat waktu'}"
if terlambat:
    st.warning(f"{status_msg} Denda: Rp {denda}")
else:
    st.success(f"{status_msg} Tidak ada denda.")

with col2:
    if st.button("✅ Absen Sekarang", key="absen_btn", use_container_width=True):
        sheet.append_row([
            tanggal_sekarang.strftime("%Y-%m-%d"),
            nama_guru,
            tanggal_sekarang.strftime("%H:%M:%S"),
            status_piket,
            denda
        ])
        st.success("Absensi berhasil dicatat!")
        if terlambat:
            kirim_telegram(f"⚠️ {nama_guru} TERLAMBAT pada {tanggal_sekarang.strftime('%H:%M:%S')} Denda: Rp {denda}")

# ---------------------------
# Ambil Data
# ---------------------------
data = sheet.get_all_records()
df_all = pd.DataFrame(data)

# ---------------------------
# Rekap Hari Ini
# ---------------------------
st.subheader("📊 Rekap Absensi Hari Ini")
if not df_all.empty:
    df_hari = df_all[df_all['Tanggal'] == tanggal_sekarang.strftime("%Y-%m-%d")]
    st.dataframe(df_hari, height=250)
    csv_hari = df_hari.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Rekap Hari Ini (CSV)",
        data=csv_hari,
        file_name=f"rekap_absensi_{tanggal_sekarang.strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# ---------------------------
# Rekap Bulanan & Grafik
# ---------------------------
st.subheader("📈 Rekap Bulanan Guru Terlambat")
if not df_all.empty:
    df_all['Bulan'] = pd.to_datetime(df_all['Tanggal']).dt.strftime('%B %Y')
    rekap_bulan = df_all[df_all['Denda']>0].groupby(['Bulan','Nama']).agg(
        Jumlah_Terlambat=('Denda','count'),
        Total_Denda=('Denda','sum')
    ).reset_index()
    
    # Highlight warna
    def highlight_denda(val):
        color = 'red' if val > 0 else 'green'
        return f'background-color: {color}; color: white'
    st.dataframe(rekap_bulan.style.applymap(highlight_denda, subset=['Total_Denda']), height=300)

    # CSV Bulanan
    csv_bulan = rekap_bulan.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Rekap Bulanan (CSV)",
        data=csv_bulan,
        file_name=f"rekap_bulanan_absensi.csv",
        mime="text/csv",
        use_container_width=True
    )

    # PDF Bulanan
    if st.button("📄 Download Rekap Bulanan (PDF)", key="pdf_btn"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Rekap Bulanan Guru SD", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(50, 8, "Bulan", 1)
        pdf.cell(50, 8, "Nama Guru", 1)
        pdf.cell(50, 8, "Jumlah Terlambat", 1)
        pdf.cell(40, 8, "Total Denda", 1)
        pdf.ln()
        pdf.set_font("Arial", '', 12)
        for i, row in rekap_bulan.iterrows():
            pdf.cell(50, 8, str(row['Bulan']), 1)
            pdf.cell(50, 8, str(row['Nama']), 1)
            pdf.cell(50, 8, str(row['Jumlah_Terlambat']), 1)
            pdf.cell(40, 8, f"Rp {row['Total_Denda']}", 1)
            pdf.ln()
        file_pdf = "rekap_bulanan_absensi.pdf"
        pdf.output(file_pdf)
        with open(file_pdf, "rb") as f:
            st.download_button("⬇️ Download Rekap Bulanan (PDF)", f, file_name=file_pdf, mime="application/pdf", use_container_width=True)

    # Grafik Bar Chart
    st.subheader("📊 Grafik Jumlah Terlambat per Guru")
    fig = px.bar(rekap_bulan, x='Nama', y='Jumlah_Terlambat', color='Total_Denda',
                 color_continuous_scale='Reds', text='Jumlah_Terlambat',
                 title='Jumlah Keterlambatan Guru per Bulan')
    st.plotly_chart(fig, use_container_width=True)
