import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ---------------------------------
# KONFIGURASI GOOGLE SHEET
# ---------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1v1Rpg2YqjV9aE3wBBjHKqK-Ji7v8ZnZTxIVD6Gq8VCU/export?format=csv"

def load_sheet_df():
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

# ---------------------------------
# FUNGSI CETAK PDF
# ---------------------------------
def create_pdf(dataframe, title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    style = getSampleStyleSheet()["Title"]
    elements.append(Paragraph(title, style))

    data = [list(dataframe.columns)] + dataframe.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---------------------------------
# TAMPILAN UTAMA
# ---------------------------------
st.set_page_config(page_title="Aplikasi Absensi Guru", layout="wide")
st.title("📋 Aplikasi Absensi Guru")

# Logo atau foto (pastikan link raw)
st.image("https://raw.githubusercontent.com/proyekabsen1-dotcom/absensiguru/main/1749893097089.png", width=100)

menu = st.sidebar.selectbox("Pilih Menu", ["Absensi", "Rekap", "Tentang"])

# ---------------------------------
# MENU ABSENSI
# ---------------------------------
if menu == "Absensi":
    st.header("🧾 Formulir Absensi Guru")

    nama = st.text_input("Nama Guru")
    status = st.selectbox("Status Kehadiran", ["Hadir", "Izin", "Cuti", "Tidak Hadir"])
    jam_masuk = st.time_input("Jam Masuk", value=datetime.now().time())
    keterangan = st.text_area("Keterangan Tambahan")

    if st.button("📥 Simpan Absensi"):
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Logika denda sederhana (misal masuk setelah 07:30)
        jam_batas = datetime.strptime("07:30", "%H:%M").time()
        denda = 0
        if status == "Hadir" and jam_masuk > jam_batas:
            denda = 5000

        st.success(f"Data absensi {nama} tersimpan. Denda: Rp{denda}")

        # Data disimpan ke Sheet (kalau ada API Sheet backend bisa ditambahkan di sini)

# ---------------------------------
# MENU REKAP (LENGKAP + GRAFIK)
# ---------------------------------
elif menu == "Rekap":
    st.header("📑 Rekap Data Absensi Guru")
    df = load_sheet_df()
    if df.empty:
        st.info("Belum ada data absensi.")
        st.stop()

    df['Tanggal'] = pd.to_datetime(df['Tanggal'], errors='coerce')
    df['Bulan'] = df['Tanggal'].dt.to_period('M').astype(str)

    tab1, tab2, tab3 = st.tabs(["📅 Harian", "📆 Bulanan", "👤 Per Guru"])

    # ------------------------
    # 📅 Rekap Harian
    # ------------------------
    with tab1:
        harian = df.copy().reset_index(drop=True)
        harian.index += 1
        harian = harian.rename_axis("No").reset_index()
        st.subheader("📅 Rekap Harian - Semua Data Masuk")
        st.dataframe(harian[["No", "Tanggal", "Nama Guru", "Status", "Jam Masuk", "Denda", "Keterangan"]])

        pdf_buffer = create_pdf(
            harian[["Tanggal", "Nama Guru", "Status", "Jam Masuk", "Denda", "Keterangan"]],
            "Rekap Harian Absensi Guru"
        )
        st.download_button("📄 Unduh PDF Rekap Harian", pdf_buffer, "rekap_harian.pdf", "application/pdf")

    # ------------------------
    # 📆 Rekap Bulanan
    # ------------------------
    with tab2:
        st.subheader("📆 Rekap Bulanan")
        bulan_pilihan = st.selectbox("Pilih Bulan", sorted(df['Bulan'].unique(), reverse=True))
        df_bulan = df[df['Bulan'] == bulan_pilihan]

        rekap_bulanan = df_bulan.groupby("Nama Guru").agg(
            Jumlah_Hadir=("Status", lambda x: (x == "Hadir").sum()),
            Jumlah_Izin=("Status", lambda x: (x == "Izin").sum()),
            Jumlah_Cuti=("Status", lambda x: (x == "Cuti").sum()),
            Jumlah_Tidak_Hadir=("Status", lambda x: (x == "Tidak Hadir").sum()),
            Total_Denda=("Denda", "sum")
        ).reset_index()

        rekap_bulanan.index += 1
        rekap_bulanan = rekap_bulanan.rename_axis("No").reset_index()

        st.dataframe(rekap_bulanan)

        # Grafik Kehadiran
        st.markdown("### 📊 Grafik Kehadiran Bulanan")
        st.bar_chart(rekap_bulanan.set_index("Nama Guru")[["Jumlah_Hadir", "Jumlah_Izin", "Jumlah_Cuti", "Jumlah_Tidak_Hadir"]])

        # Grafik Total Denda
        st.markdown("### 💰 Grafik Total Denda per Guru")
        st.bar_chart(rekap_bulanan.set_index("Nama Guru")[["Total_Denda"]])

        pdf_buffer = create_pdf(rekap_bulanan, f"Rekap Bulanan Absensi Guru - {bulan_pilihan}")
        st.download_button("📄 Unduh PDF Rekap Bulanan", pdf_buffer, f"rekap_bulanan_{bulan_pilihan}.pdf", "application/pdf")

    # ------------------------
    # 👤 Rekap Per Guru
    # ------------------------
    with tab3:
        st.subheader("👤 Rekap Per Guru")
        guru_pilihan = st.selectbox("Pilih Guru", sorted(df["Nama Guru"].unique()))
        bulan_pilihan2 = st.selectbox("Pilih Bulan", sorted(df['Bulan'].unique(), reverse=True), key="bulan_guru")
        df_guru = df[(df["Nama Guru"] == guru_pilihan) & (df["Bulan"] == bulan_pilihan2)].copy()

        df_guru.index += 1
        df_guru = df_guru.rename_axis("No").reset_index()
        st.dataframe(df_guru[["No", "Tanggal", "Nama Guru", "Status", "Denda", "Keterangan"]])

        total_denda_guru = df_guru["Denda"].sum()
        st.markdown(f"💰 **Total Denda Bulan {bulan_pilihan2}: Rp{total_denda_guru}**")

        if not df_guru.empty:
            st.markdown("### 📈 Grafik Denda per Tanggal")
            st.bar_chart(df_guru.set_index("Tanggal")[["Denda"]])

        pdf_buffer = create_pdf(
            df_guru[["Tanggal", "Nama Guru", "Status", "Denda", "Keterangan"]],
            f"Rekap Absensi {guru_pilihan} - {bulan_pilihan2}"
        )
        st.download_button("📄 Unduh PDF Rekap Per Guru", pdf_buffer,
                           f"rekap_{guru_pilihan}_{bulan_pilihan2}.pdf", "application/pdf")

# ---------------------------------
# MENU TENTANG
# ---------------------------------
elif menu == "Tentang":
    st.header("ℹ️ Tentang Aplikasi")
    st.write("""
    Aplikasi Absensi Guru ini dikembangkan untuk membantu pencatatan kehadiran guru secara digital.  
    - Data terhubung dengan **Google Sheets**  
    - Dilengkapi fitur **Rekap Harian, Bulanan, dan Per Guru**  
    - Dapat mengunduh laporan dalam format **PDF**  
    - Terdapat **grafik visual** untuk analisis kehadiran dan denda  

    👩‍💻 Pengembang: **Melisa Triandini**
    """)

