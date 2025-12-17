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
