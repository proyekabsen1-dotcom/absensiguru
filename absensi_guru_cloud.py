# ---------------------------
# ABSENSI PAGE
# ---------------------------
if menu == "Absensi":
    now = datetime.now()
    placeholder = st.empty()
    with placeholder.container():
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

    # Update jam real-time
    for _ in range(10):
        now = datetime.now()
        placeholder.markdown(f"**Tanggal:** {now.strftime('%A, %d %B %Y')}  \n⏰ **Waktu:** {now.strftime('%H:%M:%S')}")
        time.sleep(1)

    # ---------------------------
    # REKAP HARI INI DI BAWAH FORM
    # ---------------------------
    st.subheader("📋 Rekap Absensi Hari Ini")
    df_today = load_sheet_df()
    if not df_today.empty:
        df_today['Tanggal'] = pd.to_datetime(df_today['Tanggal'])
        df_today = df_today[df_today['Tanggal'].dt.date == datetime.now().date()]
        if df_today.empty:
            st.info("Belum ada guru yang absen hari ini.")
        else:
            # Fungsi memberi warna berdasarkan status
            def warna_status(status):
                if status == "Hadir":
                    return 'background-color: #d4edda'  # hijau muda
                elif status in ["Izin","Cuti"]:
                    return 'background-color: #fff3cd'  # kuning muda
                elif status == "Tidak Hadir":
                    return 'background-color: #f8d7da'  # merah muda
                return ''
            
            st.dataframe(
                df_today[["Nama Guru","Status","Jam Masuk","Denda","Keterangan"]]
                .style.applymap(warna_status, subset=["Status"])
                .format({"Denda": "Rp {:,.0f}"})
            )
