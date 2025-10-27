# absensi_guru_cloud.py
import streamlit as st
from datetime import datetime, time
import pandas as pd
import sqlite3
from fpdf import FPDF

st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# ---------------------------
# Koneksi database SQLite
# ---------------------------
conn = sqlite3.connect("absensi.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS absensi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal TEXT,
    nama TEXT,
    jam TEXT,
    status_piket TEXT,
    denda INTEGER
)
""")
conn.commit()

# ---------------------------
# Data Guru (pastikan terisi semua guru)
# ---------------------------
guru_list = ["Yolan", "Husnia", "Rima", "Rifa", "Sela", "Ustadz A", "Ustadz B", "Ustadz C"]

# ---------------------------
# Header
# ---------------------------
st.markdown("<h1 style='text-align: center; color: blue;'>Absensi Guru SD Tahfidz BKQ</h1>", unsafe_allow_html=True)
tanggal_sekarang = datetime.now()
st.markdown(f"<p style='text-align: center;'>Tanggal: {tanggal_sekarang.strftime('%A, %d %B %Y')}<br>Jam: {tanggal_sekarang.strftime('%H:%M:%S')}</p>", unsafe_allow_html=True)

# ---------------------------
# Input guru & piket
# ---------------------------
st.subheader("Input Absensi")
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

if terlambat:
    st.warning(f"{nama_guru} TERLAMBAT! Denda: Rp {denda}")
else:
    st.success(f"{nama_guru} hadir tepat waktu. Tidak ada denda.")

if st.button("Absen Sekarang", key="absen_btn"):
    c.execute(
        "INSERT INTO absensi (tanggal, nama, jam, status_piket, denda) VALUES (?, ?, ?, ?, ?)",
        (
            tanggal_sekarang.strftime("%Y-%m-%d"),
            nama_guru,
            tanggal_sekarang.strftime("%H:%M:%S"),
            status_piket,
            denda
        )
    )
    conn.commit()
    st.success("Absensi berhasil dicatat!")

# ---------------------------
# Rekap Hari Ini
# ---------------------------
st.subheader("Rekap Absensi Hari Ini")
df_hari = pd.read_sql(
    "SELECT * FROM absensi WHERE tanggal = ?",
    conn,
    params=(tanggal_sekarang.strftime("%Y-%m-%d"),)
)
st.dataframe(df_hari, height=250)

csv_hari = df_hari.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Rekap Hari Ini (CSV)",
    data=csv_hari,
    file_name=f"rekap_absensi_{tanggal_sekarang.strftime('%Y-%m-%d')}.csv",
    mime="text/csv"
)

# ---------------------------
# Rekap Bulanan
# ---------------------------
st.subheader("Rekap Bulanan Guru Terlambat")
df_all = pd.read_sql("SELECT * FROM absensi", conn)
if not df_all.empty:
    df_all['Bulan'] = pd.to_datetime(df_all['tanggal']).dt.strftime('%B %Y')
    rekap_bulan = df_all[df_all['denda']>0].groupby(['Bulan','nama']).agg(
        Jumlah_Terlambat=('denda','count'),
        Total_Denda=('denda','sum')
    ).reset_index()
    st.dataframe(rekap_bulan, height=250)

    csv_bulan = rekap_bulan.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Rekap Bulanan (CSV)",
        data=csv_bulan,
        file_name=f"rekap_bulanan_absensi.csv",
        mime="text/csv"
    )

    if st.button("Download Rekap Bulanan (PDF)", key="pdf_btn"):
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
            pdf.cell(50, 8, str(row['nama']), 1)
            pdf.cell(50, 8, str(row['Jumlah_Terlambat']), 1)
            pdf.cell(40, 8, f"Rp {row['Total_Denda']}", 1)
            pdf.ln()
        file_pdf = "rekap_bulanan_absensi.pdf"
        pdf.output(file_pdf)
        st.success(f"PDF berhasil dibuat: {file_pdf}")
        st.write(f"[Klik untuk download PDF]({file_pdf})")
else:
    st.write("Belum ada data bulanan.")
