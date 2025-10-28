# absensi_guru_cloud.py
import streamlit as st
from datetime import datetime, time
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import plotly.express as px

st.set_page_config(page_title="Absensi Guru SD Tahfidz BKQ", layout="wide")

# ---------------------------
# Config & Secrets
# ---------------------------
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", None)
GOOGLE_SERVICE_ACCOUNT = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", None)

if SPREADSHEET_URL is None or GOOGLE_SERVICE_ACCOUNT is None:
    st.error("Secrets belum lengkap. Pastikan SPREADSHEET_URL dan GOOGLE_SERVICE_ACCOUNT sudah diisi di Streamlit Secrets.")
    st.stop()

# ---------------------------
# Auth ke Google Sheets
# ---------------------------
try:
    # Jika secrets berupa string multi-line, ubah jadi dict
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

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scopes)
gc = gspread.authorize(creds)

# ---------------------------
# Buka atau buat worksheet "Absensi"
# ---------------------------
try:
    sh = gc.open_by_url(SPREADSHEET_URL)
except Exception as e:
    st.error("Gagal membuka spreadsheet. Periksa SPREADSHEET_URL dan permission service account.")
    st.stop()

# Pilih worksheet bernama "Absensi" jika ada, kalau tidak ada buat baru
sheet_title = "Absensi"
try:
    worksheet = sh.worksheet(sheet_title)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=sheet_title, rows="1000", cols="20")
    # Buat header default
    header = ["Tanggal", "Nama Guru", "Status", "Jam Masuk", "Jam Pulang", "Denda", "Keterangan"]
    worksheet.append_row(header)

# ---------------------------
# Daftar guru (sesuaikan jika perlu)
# ---------------------------
guru_list = ["Yolan", "Husnia", "Rima", "Rifa", "Sela", "Ustadz A", "Ustadz B", "Ustadz C"]

# ---------------------------
# Navigasi Menu
# ---------------------------
menu = st.sidebar.radio("📌 Menu", ["Absensi", "Rekap", "Grafik"])

# Utility: baca semua data dari worksheet ke DataFrame
@st.cache_data(ttl=30)
def load_sheet_df():
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
        else:
            df = pd.DataFrame(columns=["Tanggal","Nama Guru","Status","Jam Masuk","Jam Pulang","Denda","Keterangan"])
        return df
    except Exception as e:
        st.error(f"Gagal membaca data dari Google Sheet: {e}")
        return pd.DataFrame(columns=["Tanggal","Nama Guru","Status","Jam Masuk","Jam Pulang","Denda","Keterangan"])

# ---------------------------
# Absensi Page
# ---------------------------
if menu == "Absensi":
    st.title("📌 Absensi Guru SD Tahfidz BKQ")

    tanggal_sekarang = datetime.now()
    st.markdown(f"**Tanggal:** {tanggal_sekarang.strftime('%A, %d %B %Y')} — **Jam:** {tanggal_sekarang.strftime('%H:%M:%S')}")

    st.subheader("Input Absensi")
    with st.form("form_absen", clear_on_submit=True):
        col1, col2 = st.columns([2,2])
        with col1:
            nama_guru = st.selectbox("Nama Guru", guru_list)
        with col2:
            status = st.selectbox("Status", ["Hadir", "Izin", "Sakit", "Alpha", "Telat (Piket)", "Telat (Biasa)"])
        jam_masuk = st.text_input("Jam Masuk (HH:MM) — kosongkan untuk auto", value=tanggal_sekarang.strftime("%H:%M:%S"))
        jam_pulang = st.text_input("Jam Pulang (HH:MM) — optional", value="")
        keterangan = st.text_input("Keterangan (opsional)", value="")

        submitted = st.form_submit_button("Absen Sekarang")
        if submitted:
            # Logika denda: jika status telat (dua jenis) set denda 2000
            denda = 0
            if status.startswith("Telat"):
                denda = 2000

            # Prepare row sesuai header
            row = [
                tanggal_sekarang.strftime("%Y-%m-%d"),
                nama_guru,
                "Hadir" if status == "Hadir" else status,  # keep values
                jam_masuk,
                jam_pulang,
                denda,
                keterangan
            ]

            try:
                worksheet.append_row(row)
                # refresh cached data
                load_sheet_df.clear()
                st.success("Absensi berhasil dicatat dan tersimpan ke Google Spreadsheet ✅")
            except Exception as e:
                st.error(f"Gagal menyimpan ke Google Sheets: {e}")

# ---------------------------
# Rekap Page
# ---------------------------
elif menu == "Rekap":
    st.title("📑 Rekap Data Absensi")
    df = load_sheet_df()

    if df.empty:
        st.info("Belum ada data absensi.")
    else:
        # Tampilkan preview
        st.dataframe(df, height=400)

        # Filter by Guru / Tanggal
        st.subheader("Filter")
        cols = st.columns(3)
        with cols[0]:
            guru_filter = st.selectbox("Pilih Guru (Semua jika kosong)", ["Semua"] + guru_list)
        with cols[1]:
            date_min = st.date_input("Dari tanggal", value=pd.to_datetime(df['Tanggal']).min() if not df.empty else None)
        with cols[2]:
            date_max = st.date_input("Sampai tanggal", value=pd.to_datetime(df['Tanggal']).max() if not df.empty else None)

        # Apply filters
        df_filtered = df.copy()
        df_filtered['Tanggal'] = pd.to_datetime(df_filtered['Tanggal'])
        if guru_filter != "Semua":
            df_filtered = df_filtered[df_filtered['Nama Guru'] == guru_filter]
        if date_min is not None:
            df_filtered = df_filtered[df_filtered['Tanggal'] >= pd.to_datetime(date_min)]
        if date_max is not None:
            df_filtered = df_filtered[df_filtered['Tanggal'] <= pd.to_datetime(date_max)]

        st.write(f"Menampilkan {len(df_filtered)} baris.")
        st.dataframe(df_filtered, height=300)

        # Download CSV
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("Download Rekap (CSV)", data=csv, file_name="rekap_absensi.csv", mime="text/csv")

# ---------------------------
# Grafik Page
# ---------------------------
elif menu == "Grafik":
    st.title("📊 Grafik Absensi Guru")
    df = load_sheet_df()

    if df.empty:
        st.info("Belum ada data untuk divisualisasikan.")
    else:
        # Prepare data
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        # Pastikan kolom 'Status' konsisten
        df['Status'] = df['Status'].astype(str)

        # Chart 1: Kehadiran per Guru (stacked by status)
        st.subheader("📊 Kehadiran per Guru (berdasarkan Status)")
        hadir_count = df.groupby(['Nama Guru', 'Status']).size().reset_index(name='Jumlah')
        fig1 = px.bar(hadir_count, x='Nama Guru', y='Jumlah', color='Status',
                      title='Jumlah Kehadiran / Status per Guru', barmode='stack')
        st.plotly_chart(fig1, use_container_width=True)

        # Chart 2: Tren Harian (total absensi per hari)
        st.subheader("📈 Tren Absensi Harian")
        harian = df.groupby('Tanggal').size().reset_index(name='Jumlah')
        fig2 = px.line(harian, x='Tanggal', y='Jumlah', markers=True, title='Jumlah Absensi per Hari')
        st.plotly_chart(fig2, use_container_width=True)

        # Chart 3: Persentase Status (pie)
        st.subheader("🥧 Persentase Status Kehadiran")
        status_persen = df['Status'].value_counts().reset_index()
        status_persen.columns = ['Status', 'Jumlah']
        fig3 = px.pie(status_persen, names='Status', values='Jumlah', title='Persentase Status Kehadiran')
        st.plotly_chart(fig3, use_container_width=True)

        # Optional: show aggregated table per month
        st.subheader("📋 Rekap Bulanan Keterlambatan")
        df['Bulan'] = df['Tanggal'].dt.to_period('M').astype(str)
        terlambat_df = df[df['Denda'].astype(float) > 0] if 'Denda' in df.columns else pd.DataFrame()
        if not terlambat_df.empty:
            rekap_bulan = terlambat_df.groupby(['Bulan', 'Nama Guru']).agg(
                Jumlah_Terlambat=('Denda', 'count'),
                Total_Denda=('Denda', 'sum')
            ).reset_index()
            st.dataframe(rekap_bulan, height=300)
        else:
            st.info("Belum ada catatan keterlambatan untuk direkap.")

# ---------------------------
# End of file
# ---------------------------

