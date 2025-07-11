import numpy as np
import face_recognition
import cv2
import os
import time
import requests
import shutil

# Coba impor pustaka face_recognition, instal jika belum ada
try:
    import face_recognition
    from tqdm import tqdm 
    import pickle
    import cv2
    from ultralytics import YOLO
    import numpy as np
    import json
    import serial
    import serial.tools.list_ports
    from datetime import datetime
    from datetime import date
except ImportError:
    print("Library tidak ditemukan, menginstal sekarang...")
    os.system(
        "pip install numpy==1.24.3 face_recognition==1.3.0 tqdm==4.67.0 pickle-mixin==1.0.2 opencv-python==4.10.0.84 ultralytics==8.3.32 requests==2.32.3 pyserial==3.5 keyboard==0.13.5")

    from tqdm import tqdm
    import pickle
    import cv2
    from ultralytics import YOLO
    import numpy as np
    import face_recognition  # Coba impor kembali setelah instalasi
    import json
    import serial
    import serial.tools.list_ports
    from datetime import datetime
    from datetime import date

# Inisialisasi timer
timer_start = None
timer1 = 0
timer2 = 0
nama = ""
id = ""
sekali_kirim = 0
elapsed_time = 0
remaining_time = 0
start_encoding = 0

# Mendapatkan folder saat ini
current_directory = os.path.dirname(os.path.abspath(__file__))

print("Tanggal :", str(date.today()))
print("Folder saat ini:", current_directory)

#######################################################################
# Default config
config_path = os.path.join(current_directory, 'config.json')
default_config = {
"kamera" : 0,
"timer_verifikasi" : 5,  # Timer countdown dalam detik
"folder_wajah" : "dataset_wajah",
"model_yolo" : "model_yolov8.pt",
"toleransi" : 0.5 , # semakin kecil semakin detail perbedaan wajah, tapi sensitifitas berkurang,
"timer" : 5,  # absensi dimulai setelah wajah terdeteksi selama 5 detik
"baudrate": 115200,
"encoding_path" : "encoding_wajah.bin"
}

########################################################################
# jangan diubah, jgn dihapus
url = "https://localhost.scode.web.id/2025-rivaldo-security-pintu-facerecognition/api/api.php"
url_absen = "https://localhost.scode.web.id/2025-rivaldo-security-pintu-facerecognition/api/api.php?id_wajah="


# Cek dan buat file config jika belum ada
if not os.path.exists(config_path):
    with open(config_path, 'w') as file:
        json.dump(default_config, file, indent=4)

# Baca config
with open(config_path, 'r') as file:
    config = json.load(file)

data_dataset = []
data_semua = {}
data_nama = []
status_nama = []
konfirmasi_nama = []
# Load YOLO model
yolo_model = YOLO(config["model_yolo"])
# Open the camera
cam = cv2.VideoCapture(config["kamera"])
timer_verifikasi = config["timer_verifikasi"]  
durasi_deteksi = config["durasi_deteksi"]
folder_wajah = config["folder_wajah"]
toleransi = config["toleransi"] 
timer = config["timer"] 
ports = serial.tools.list_ports.comports()
baud_rate = config["baudrate"]
encoding_path = os.path.join(current_directory,config["encoding_path"]) 



# Check if the camera is opened successfully

if not cam.isOpened():
    while (1):
        print("Error: Could not open camera.")
        print("Periksa nomor kamera / sambungan kamera ... ")
        time.sleep(1)
else:
    print("Camera opened successfully.")
    response = requests.get(url_absen)

def proses_kirim_serial(pesan):
    pesan = pesan +"\n"
    global ser
    if pesan == "inisiasi\n":
        try:
            print("MENCARI PORT OTOMATIS .......... ")
            print(ports)
            gagal = 0
            for k in ports:
                try:
                    print("Mencoba port", k)
                    k = str(k).split(" ")[0]
                    ser = serial.Serial(k, baud_rate, timeout=0.5, write_timeout=0.5)
                    print(f"Terhubung ke {k} dengan baud rate {baud_rate}")
                    time.sleep(1)
                    break
                except:
                    print("Gagal Terhubung", k)
                    gagal += 1
                    time.sleep(0.1)

            if len(ports) == 0:
                print("TIDAK ADA PORT SERIAL")

            if gagal == len(ports):
                print("Port terdeteksi:", ports)
                print("Pastikan port tidak dibuka di aplikasi lain !!")
                port_serial = input("Masukkan nama port serial yang benar: ")
                ser = serial.Serial(port_serial, baud_rate, timeout=0.5, write_timeout=0.5)

            time.sleep(2)  # tunggu koneksi stabil
        except serial.SerialException as e:
            print(f"Gagal membuka port serial: {e}")

    elif pesan == "get_sensor\n":
        ser.write(pesan.encode())
        print("Mengirim permintaan sensor:", pesan)
        data = ""
        while (1):
            ser.write(pesan.encode())
            time.sleep(0.1)
            data = ser.readline().decode('utf-8', errors='ignore').strip()
            if (len(data) > 0):
                break
            
            
            
        data = data.strip()
        print("Data Sensor Diterima:", data)
        return data

    else:
        ser.write(pesan.encode())
        print("Mengirim pesan serial:", pesan.encode())



def web(message):
    global url_absen
    response = requests.get(url_absen+message)

    print(response)
    time.sleep(2)


def hapus_semua_dalam_folder(folder_path):
    # Membaca data dataset yang ada
    if not os.path.exists(folder_wajah):
        os.mkdir(folder_wajah)

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)  # Hapus file atau symlink
            elif os.path.isdir(item_path):
                hapus_semua_dalam_folder(item_path)  # Hapus isi subfolder dulu
                os.rmdir(item_path)  # Hapus subfolder setelah kosong
        except Exception as e:
            print(f"Gagal menghapus {item_path}: {e}")

def image_manager():
    global url, data_dataset, folder_wajah, start_encoding
    print("image manager")

    folder_dummy = "dummy"

    # Buat folder dummy jika belum ada
    if not os.path.exists(folder_dummy):
        os.mkdir(folder_dummy)

    # Ambil data orang dari server
    respon = requests.get(url=url)
    print(respon.text)

    # Proses setiap orang dan simpan ke folder dummy
    for orang in eval(respon.text):
        id = orang["id"]
        nama = orang["nama"]

        nama_folder_dummy = os.path.join(folder_dummy, id + "_" + nama)
        os.makedirs(nama_folder_dummy, exist_ok=True)

        for i in range(10):
            url_gambar = orang["foto" + str(i + 1)]
            url_gambar = url_gambar.replace("\\", "").replace("////", "//")
            print("URL : ", url_gambar)

            try:
                gambar_respon = requests.get(url_gambar)
                if gambar_respon.status_code == 200:
                    path_dummy = os.path.join(
                        nama_folder_dummy, nama + "_" + str(i + 1) + ".jpg")
                    with open(path_dummy, "wb") as f:
                        f.write(gambar_respon.content)
                else:
                    print(f"Gagal mengunduh gambar dari {url_gambar}")
            except Exception as e:
                print(f"Error saat mengunduh: {e}")

    # Hitung total ukuran file di folder dummy
    def total_ukuran_folder(path):
        total = 0
        for root, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(root, file)
                total += os.path.getsize(full_path)
        return total

    ukuran_dummy = total_ukuran_folder(folder_dummy)
    ukuran_wajah = total_ukuran_folder(folder_wajah) if os.path.exists(folder_wajah) else 0

    print(f"Ukuran dummy: {ukuran_dummy / 1024:.2f} KB")
    print(f"Ukuran wajah: {ukuran_wajah / 1024:.2f} KB")

    # Bandingkan, jika beda maka ganti isi folder wajah
    if ukuran_dummy != ukuran_wajah:
        print("Ukuran berbeda, mengganti isi folder wajah")
        start_encoding = 1
        # Hapus semua isi folder wajah
        if os.path.exists(folder_wajah):
            shutil.rmtree(folder_wajah)
        os.makedirs(folder_wajah, exist_ok=True)

        # Pindahkan isi folder dummy ke folder wajah
        for nama_subfolder in os.listdir(folder_dummy):
            asal = os.path.join(folder_dummy, nama_subfolder)
            tujuan = os.path.join(folder_wajah, nama_subfolder)
            shutil.move(asal, tujuan)

    # Hapus folder dummy
    shutil.rmtree(folder_dummy)

    # Perbarui data_dataset
    data_dataset.clear()
    for k in os.listdir(folder_wajah):
        for l in os.listdir(os.path.join(folder_wajah, k)):
            data_dataset.append(l)

    print("Selesai. Data dataset:", data_dataset)

def encoding_wajah():
    global data_nama, data_semua, folder_wajah, yolo_model, encoding_path
    print("Mulai proses Encoding (perlu waktu tergantung jumlah foto)")

    for nama in os.listdir(folder_wajah):
        poto = []
        sub_folder = os.path.join(folder_wajah, nama)

        if os.path.isdir(sub_folder):
            for b in tqdm(os.listdir(sub_folder)):
                path_image = os.path.join(sub_folder, b)

                if os.path.isfile(path_image):
                    frame = cv2.imread(path_image)
                    results = yolo_model(frame)

                    for r in results:
                        boxes = r.boxes.xyxy.tolist()
                        for box in boxes:
                            x1, y1, x2, y2 = map(int, box[:4])

                            # Simpan kotak dari YOLO pada frame asli
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Hijau: YOLO

                            # Deteksi wajah pada hasil crop
                            face_locations = face_recognition.face_locations(frame)
                            face_encodings = face_recognition.face_encodings(frame, face_locations)

                            for (top, right, bottom, left) in face_locations:
                                # Gambar kotak wajah dari face_recognition (biru)
                                cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)

                            # Resize hasil crop untuk ditampilkan (tetap 480x480)
                            display_frame = cv2.resize(frame, (480, 480))
                            cv2.imshow("Deteksi Wajah", display_frame)
                            cv2.waitKey(500)

                            if face_encodings:
                                poto.append(face_encodings[0])

        if poto:
            data_semua[nama] = poto
            print(f"{nama} selesai.")
        else:
            print("WAJAH TIDAK ADA PADA GAMBAR.")
            while True:
                pass

    with open(encoding_path, "wb") as f:
        pickle.dump(data_semua, f)
    print("Data encoding disimpan dalam file encoding_wajah.bin")
    cv2.destroyAllWindows()

def inisiasi():
    global data_semua, data_nama, folder_wajah,start_encoding

    print(" >>>>>  Jika ada perubahan pada folder nama / foto, wajib menghapus file encoding_wajah.bin <<<<<  ")
    time.sleep(3)
    image_manager()

    try:
        with open(encoding_path, "rb") as f:
            print("Memuat data encoding sebelumnya .. ")
            data_semua = pickle.load(f)
            f.close()
    except:
        print("Gagal memuat data encoding sebelumnya, membuat file baru ...")
        encoding_wajah()

    data_nama = list(data_semua.keys())
    print("Data nama : ", data_nama)

    if data_nama != os.listdir(folder_wajah) or start_encoding == 1 :
        print("perubahan data terdeteksi, membuat encoding baru ... ")
        os.remove(encoding_path)
        data_nama = []
        data_semua = {}
        encoding_wajah()
        with open(encoding_path, "rb") as f:
            print("Memuat data encoding yang telah dibuat .. ")
            data_semua = pickle.load(f)
            f.close()

        data_nama = list(data_semua.keys())
        print("Data nama : ", data_nama)
        start_encoding = 0

    for l in (data_nama):
        status_nama.append(0)
        konfirmasi_nama.append(0)


def deteksi():
    global timer_start, timer_deteksi, elapsed_time, sekali_kirim, last_detected_name, timer_verifikasi, nama, id, data_nama

    # Inisialisasi variabel
    timer_start = None
    timer_deteksi = 0
    elapsed_time = 0
    sekali_kirim = False
    last_detected_name = None

    while True:
        # Baca frame dari kamera
        res, frame = cam.read()
        nama_terdeteksi = None
        data = proses_kirim_serial("get_sensor")
        print("data : ",data)

        if data == "1":
            timer_deteksi = time.time()

        durasi = time.time() - timer_deteksi
        print( durasi)
        if durasi < durasi_deteksi :
            cv2.putText(frame,f"DETEKSI AKTIF ({durasi_deteksi - int(durasi)}) ", (0, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            print("DETEKSI AKTIF ... ", int(time.time() - timer_deteksi))
            # Periksa apakah frame berhasil dibaca
            if not res:
                print("Error: Could not read frame.")
                break

            # Jalankan YOLO untuk deteksi
            results = yolo_model(frame)

            # Loop setiap hasil deteksi
            if len(results) == 1:
                nama_terdeteksi = "Tidak Dikenali"
                nama = nama_terdeteksi
                id = ""
                for r in results:
                    boxes = r.boxes.xyxy.tolist()
                    for box in boxes:
                        # Ekstraksi koordinat bounding box
                        x1, y1, x2, y2 = map(int, box[:4])

                        # Potong dan proses gambar untuk pengenalan wajah
                        if y1 >= 20:
                            image_rgb = frame[y1-20:y2, x1:x2]
                            cv2.rectangle(frame, (x1, y1-20),
                                        (x2, y2), (0, 255, 0), 2)
                        else:
                            image_rgb = frame[y1:y2, x1:x2]
                            cv2.rectangle(frame, (x1, y1),
                                        (x2, y2), (0, 255, 0), 2)

                        # Penyesuaian kontras dan kecerahan
                        alpha = 1.5
                        beta = 20
                        image_rgb = cv2.convertScaleAbs(
                            image_rgb, alpha=alpha, beta=beta)

                        input_face_encodings = face_recognition.face_encodings(
                            image_rgb)

                        koordinat = 0
                        # Cek kecocokan dengan data wajah yang dikenal
                        for k in data_nama:
                            konfirmasi_nama[data_nama.index(k)] = 0
                            for l in data_semua[k]:
                                matches = face_recognition.compare_faces(
                                    [l], input_face_encodings[0], tolerance=toleransi) if input_face_encodings else []
                                if True in matches:
                                    konfirmasi_nama[data_nama.index(k)] += 1

                            koordinat += 10

                            probabilitas = (
                                konfirmasi_nama[data_nama.index(k)] / len(data_semua[k]) * 100)
                            print("Probabilitas : ", k,
                                probabilitas, "%")
                            # Tampilkan nama di frame
                            cv2.putText(frame, k.split("_")[1] + " " +
                                        str(round(probabilitas, 1)) +
                                        "%", (0, 60 + koordinat*2),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

                            if (konfirmasi_nama[np.argmax(konfirmasi_nama)] != 0):
                                nama_terdeteksi = data_nama[np.argmax(
                                    konfirmasi_nama)]

                            try:
                                nama = nama_terdeteksi.split("_")[1]
                                id = nama_terdeteksi.split("_")[0]
                            except:
                                pass

                        # Tampilkan nama di frame
                        cv2.putText(frame, nama, (x1, y1 - 80),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        cv2.putText(frame, id, (x1, y1 - 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # Logika Timer
            if nama_terdeteksi != "Tidak Dikenali":
                # kode untuk kontrol esp32
            

                if nama_terdeteksi != last_detected_name:
                    # Nama baru terdeteksi, reset timer
                    timer_start = time.time()
                    sekali_kirim = False
                    last_detected_name = nama_terdeteksi

                elapsed_time = time.time() - timer_start
                remaining_time = timer_verifikasi - elapsed_time
                if remaining_time < 0:
                    remaining_time = 0

                if remaining_time <= 0 and not sekali_kirim:
                    print("....................... MENGIRIM ABSEN ........................")
                    proses_kirim_serial("@"+nama)
                    sekali_kirim = True
                    cv2.putText(frame, "MENGIRIM ABSEN ...", (0, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                    web(id)

            else:
                # Reset jika tidak ada nama yang terdeteksi
                timer_start = None
                elapsed_time = 0
                sekali_kirim = False
                last_detected_name = None

            # Tampilkan timer di frame
            if timer_start:
                cv2.putText(frame, f"Status : ({round(remaining_time, 1)}s)", (0, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        # Tampilkan frame
        cv2.imshow('YOLO Detection', frame)

        # Tombol keluar
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Bersihkan sumber daya
    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    inisiasi()
    proses_kirim_serial("inisiasi")
    deteksi()
