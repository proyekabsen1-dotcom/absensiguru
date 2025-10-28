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
