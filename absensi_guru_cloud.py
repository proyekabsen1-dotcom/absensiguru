import streamlit as st
from datetime import datetime, time
import pandas as pd
import sqlite3
from fpdf import FPDF
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import json
import os

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
# Koneksi Google Sheets
# ---------------------------
SPREADSHEET_URL = st.secrets["SPREADSHEET_URL"]

gc = gspread.oauth(
    scopes=['https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive']
)

sh = gc.open_by_url(SPREADSHEET_URL)
worksheet = sh.sheet1

# ---------------------------
# Data Guru
# ---------------------------
guru_list = ["Yolan", "Husnia", "Rima", "Rifa", "Sela", "Ustadz A", "Ustadz B", "Ustadz C"]

# ---------------------------
# Header
# ---------------------------
st.markdown("<h1 style='text-align: center; color: blue;'>Absensi Guru SD Tahfidz BKQ</h1>", unsafe_allow_html=True)

tanggal_sekarang = datetime.now()
st.markdown(
    f"<p style='text-align: center;'>Tanggal: {tanggal_sekarang.strftime('%A, %d %B %Y')}<br>Jam: {tanggal_sekarang.strftime('%H:%M:%S')}</p>",
    unsafe_allow_html=True
)

# ---------------------------
# Input
# ---------------------------
st.subheader("Input Absensi")
nama_guru = st.selectbox("Nama Guru", guru_list)
status_piket = st.radio("Status Piket", ["Piket", "Tidak Piket"], horizontal=True)

# Denda Logic
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
    # Simpan ke SQLite
    c.execute("INSERT INTO absensi (tanggal, nama, jam, status_piket, denda) VALUES (?, ?, ?, ?, ?)",
              (tanggal_sekarang.strftime("%Y-%m-%d"),
               nama_guru,
               tanggal_sekarang.strftime("%H:%M:%S"),
               status_piket,
               denda))
    conn.commit()

    # Backup ke Google Sheets
    worksheet.append_row([
        tanggal_sekarang.strftime("%Y-%m-%d"),
        nama_guru,
        tanggal_sekarang.strftime("%H:%M:%S"),
        status_piket,
        denda
    ])

    st.success("Absensi berhasil dicatat!")

# ---------------------------
# Rekap Hari Ini
# ---------------------------
st.subheader("Rekap Absensi Hari Ini")
df_hari = pd.read_sql("SELECT * FROM absensi WHERE tanggal = ?",
                      conn,
                      params=(tanggal_sekarang.strftime("%Y-%m-%d"),))

st.dataframe(df_hari, height=250)

# Download CSV
csv_hari = df_hari.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Rekap Hari Ini (CSV)",
    data=csv_hari,
    file_name=f"rekap_absensi_{tanggal_sekarang.strftime('%Y-%m-%d')}.csv",
    mime="text/csv"
)

# ---------------------------
# Visualisasi Grafik Bulanan
# ---------------------------
st.subheader("Grafik Keterlambatan Bulanan")

df_all = pd.read_sql("SELECT * FROM absensi", conn)

if not df_all.empty:
    df_all['Bulan'] = pd.to_datetime(df_all['tanggal']).dt.strftime('%B %Y')
    df_late = df_all[df_all["denda"] > 0]

    if not df_late.empty:
        chart = df_late.groupby(["Bulan", "nama"]).size().reset_index(name="Terlambat")
        fig = px.bar(chart, x="nama", y="Terlambat", color="Bulan", barmode="group",
                     title="Jumlah Keterlambatan Guru per Bulan")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Belum ada yang terlambat bulan ini 😊")

else:
    st.info("Belum ada data absensi.")

