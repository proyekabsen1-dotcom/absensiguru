# ---------------------------
# ABSENSI PAGE REAL-TIME DENGAN HIGHLIGHT
# ---------------------------
if menu == "Absensi":
    tz = ZoneInfo("Asia/Jakarta")
    placeholder_time = st.empty()
    placeholder_rekap = st.empty()

    with st.form("form_absen", clear_on_submit=True):
        nama_guru = st.selectbox("Nama Guru", guru_list)
        status_manual = st.selectbox("Status", ["Hadir","Izin","Cuti","Tidak Hadir"])
        keterangan = st.text_input("Keterangan (opsional)")
        submitted = st.form_submit_button("✨ Absen Sekarang", type="primary")
        if submitted:
            now = datetime.now(tz)
            tanggal = now.strftime("%Y-%m-%d")
            waktu = now.strftime("%H:%M:%S")
            jam_masuk = waktu
            denda = hitung_denda(nama_guru, jam_masuk, status_manual)
            row = [tanggal, waktu, nama_guru, status_manual, jam_masuk, denda, keterangan]
            append_absen_row(row)
            st.success(f"🎆 Absen berhasil! Tercatat: {tanggal} {waktu}  Denda: Rp{denda}")

    import threading
    import time as t

    def update_time_and_rekap():
        while True:
            now = datetime.now(tz)
            placeholder_time.markdown(f"**Tanggal:** {now.strftime('%A, %d %B %Y')}  \n⏰ **Waktu Sekarang:** {now.strftime('%H:%M:%S')}")
            
            df = load_sheet_df()
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
            df_hari_ini = df[df['Tanggal'].dt.date == now.date()]
            
            if not df_hari_ini.empty:
                # Buat highlight
                def highlight_row(row):
                    if row['Denda'] > 0:
                        return ['background-color: #f8d7da']*len(row)  # merah untuk telat
                    elif row['Status'] == 'Hadir':
                        return ['background-color: #d4edda']*len(row)  # hijau untuk hadir tepat waktu
                    else:
                        return ['background-color: #fff3cd']*len(row)  # kuning untuk izin/cuti/tidak hadir

                placeholder_rekap.dataframe(df_hari_ini.style.apply(highlight_row, axis=1))
            
            t.sleep(1)

    threading.Thread(target=update_time_and_rekap, daemon=True).start()
