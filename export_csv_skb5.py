'''
Ini adalah script untuk mengubah pdf lampiran hasil CPNS jadi csv
Caveat: kalo langsung prosess 20rb halaman, agak keselek di tengah, jadi mending di-iterate beberapa halaman
Saya yakin ada cara yang lebih elegan. Feel free to give me any suggestions
Cara run 
python export_data_to_csv.py index_halaman_start index_halaman_end
Misal
python export_data_to_csv.py 0 100
'''

import pdfplumber
import pandas as pd
import datetime as dt
import sys


def check_formasi_kosong_page(page):
    '''
    Fungsi untuk mengecek keberadaan tabel perorangan
    Input: page (ex: pdf.pages[0])
    Output: 
        - found (binary, iya tidaknya sebuah halaman punya tabel perorangan)
        - df_returned (tabel perorangan jika ada)
    '''
    found = False
    df_returned = pd.DataFrame()
    for table in page.extract_tables():
        df = pd.DataFrame(table)
        if (df.shape[1] == 11) & (df.shape[0] == 5):
            found = True
            # df_returned = df

            jumlah_formasi = df.iloc[4, 1]
            lulus_akhir = df.iloc[4, 10]
            jumlah_tms1 = df.iloc[4, 8]
            sisa_formasi = jumlah_formasi - lulus_akhir

            tms1_terbaik = 0
            if sisa_formasi < jumlah_tms1:
                tms1_terbaik = sisa_formasi
            else:
                tms1_terbaik = jumlah_tms1

    return found, tms1_terbaik


def check_for_jabatan(page):
    '''
    Fungsi untuk mengecek keberadaan informasi lowongan
    Input: page (ex: pdf.pages[0])
    Output: 
        - dicitionary berisi informasi lowongan
    '''
    if "Lokasi Formasi :" in page.extract_text():
        text = page.extract_text()
        pendidikan = page.extract_tables()[1][0][1]
        jabatan_strings = text.split("Jabatan : ")[1].split("Lokasi")[0]
        lokasi_front = ""
        jabatan = jabatan_strings.split("\n")[0]

        if len(jabatan_strings.split("\n")) > 1:
            lokasi_front = " ".join(jabatan_strings.split("\n")[1:])
        lokasi_string = text.split("Lokasi Formasi : ")[1].split("Jenis")[0]
        if len(lokasi_string.split("\n")) > 2:
            lokasi_back = " ".join(lokasi_string.split("\n")[1:])
        else:
            lokasi_back = lokasi_string.split(" - ")[1]

        return {
            "kode_jabatan": jabatan.split(" - ")[0],
            "jabatan": jabatan.split(" - ")[1],
            "kode_lokasi": lokasi_string.split(" - ")[0],
            "lokasi_formasi": lokasi_front+lokasi_back,
            "jenis_formasi": text.split("Jenis Formasi : ")[1].split("\n")[0],
            "pendidikan": pendidikan
        }
    else:
        return {}


def find_tms(df_):
    jumlah_formasi = df_.iloc[4, 1]
    lulus_akhir = df_.iloc[4, 10]
    jumlah_tms1 = df_.iloc[4, 8]
    sisa_formasi = jumlah_formasi - lulus_akhir

    tms1_terbaik = 0
    if sisa_formasi < jumlah_tms1:
        tms1_terbaik = sisa_formasi
    else:
        tms1_terbaik = jumlah_tms1
    return tms1_terbaik


def get_info_from_table(df_):
    '''
    Fungsi untuk mengekstrak informasi dari tabel perorangan 
    Input: df_ (dataframe tabel perorangan)
    Output: 
        - dicitionary berisi informasi perorangan yang telah diekstrak
    '''

    base_data = {
        "jumlah_peserta_skb": df_.iloc[4, 0],
        "jumlah_formasi": df_.iloc[4, 1],
        "jumlah_metode_skb": df_.iloc[4, 2],
        "peserta_total": df_.iloc[4, 3],
        "peserta_hadir": df_.iloc[4, 4],
        "peserta_th": df_.iloc[4, 5],
        "hasil_tl": df_.iloc[4, 6],
        "hasil_tms": df_.iloc[4, 7],
        "hasil_tms-1": df_.iloc[4, 8],
        "hasil_aps": df_.iloc[4, 9],
        "lulus_akhir": df_.iloc[4, 10],
    }

    return {**base_data}


def split_df(df_):
    '''
    Fungsi untuk split tabel perorangan. Kadang ada satu halaman dengan lebih dari satu tabel.
    Input: df_ (dataframe tabel perorangan)
    Output: 
        - list berisi beberapa dataframe untuk tiap individu
    '''
    dfs = []
    header_indexes = list(df_[df_[1] == "No Peserta"].index)
    header_indexes.append(len(df_))
    for i in range(len(header_indexes)-1):
        splitted_df = df_.iloc[header_indexes[i]: header_indexes[i+1], :]
        splitted_df.index = range(len(splitted_df))
        dfs.append(splitted_df)
    return dfs


if __name__ == "__main__":
    file_name = 'HasilIntegrasi.pdf'
    start_index = int(sys.argv[1])
    end_index = int(sys.argv[2])
    export_filename = file_name+".csv"
    pdf = pdfplumber.open(file_name)

    # start iterating
    result = []
    last_jabatan = {}

    start_time = dt.datetime.now()
    tms1_terbaik = 0
    is_formasi_kosong = False

    for i in range(start_index, end_index):
        pg = pdf.pages[i]

        # jika halaman tsb ada info tentang lowongan, simpan
        current_jabatan = check_for_jabatan(pg)
        if current_jabatan != {}:
            last_jabatan = current_jabatan

        is_detail_found, jumlah_tms1 = check_formasi_kosong_page(pg)

        if jumlah_tms1 > 0:
            tms1_terbaik = jumlah_tms1
            continue

            # jika ketemu ada tabel perorangan
        if is_detail_found:
            # splitted_df = split_df(detail_df)
            details = get_info_from_table(detail_df)
            if current_jabatan == {}:
                # kalo ada info lowongan di halaman yang sama, pakai info lowongan tsb
                details.update(last_jabatan)
            else:
                # kalo ga, pake info lowongan terakhir
                details.update(current_jabatan)
                last_jabatan = current_jabatan
            result.append(details)

        # untuk logging
        if i % 100 == 99:
            curr_time = dt.datetime.now()
            print("Done for "+str(i), curr_time-start_time)
            start_time = dt.datetime.now()

    res = pd.DataFrame(result)
    res.to_csv(export_filename)
