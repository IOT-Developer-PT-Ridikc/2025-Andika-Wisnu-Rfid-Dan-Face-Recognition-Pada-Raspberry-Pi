import os
import cv2
import numpy as np
import psutil
from tqdm import tqdm 
import cv2
import shutil
import json
import serial
import serial.tools.list_ports
from datetime import datetime
from datetime import date
import time
import requests
    
# Inisialisasi detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
# Latih model LBPH
recognizer = cv2.face.LBPHFaceRecognizer_create(
    radius=1,
    neighbors=8,
    grid_x=5,
    grid_y=5
)


# Inisialisasi
timer_start = None
timer1 = 0
timer2 = 0
nama = ""
id = ""
sekali_kirim = 0
elapsed_time = 0
remaining_time = 0
start_encoding = 0
dictionary = {}
dictionary_threshold = {}
FACE_SIZE = (400, 400)

# Mendapatkan folder saat ini
current_directory = os.path.dirname(os.path.abspath(__file__))

print("Tanggal :", str(date.today()))
print("Folder saat ini:", current_directory)
# rasberry gak bisa cari port otomatis
port_serial = "/dev/ttyUSB0"
# port_serial = "COM7"

#######################################################################
# Default config
config_path = os.path.join(current_directory, 'config.json')
default_config = {
    "kamera": 0,
    "folder_wajah": "dataset_wajah",
    "model_yolo": "model_yolov8.pt",
    "encoding_path": "encoding_wajah.bin",
    "faces_folder" : "faces",
    "path_data_th" : "data.json",
    "timer_verifikasi": 5, 
    "toleransi": 0.5,
    "timer": 5,
    "baudrate": 9600,
    "threshold" : 65
}

########################################################################
# jangan diubah, jgn dihapus
url = "https://localhost.scode.web.id/2025-andika-restu-monitoring-akses-pintu/api/api.php"
url_absen = url + "?id_wajah="
url_absen_rfid = url + "?rfid="

# Cek dan buat file config jika belum ada
if not os.path.exists(config_path):
    with open(config_path, 'w') as file:
        json.dump(default_config, file, indent=4)

# Baca config
with open(config_path, 'r') as file:
    config = json.load(file)

data_dataset = []
status_nama = []
konfirmasi_nama = []
# Load YOLO model

# Open the camera
cam = cv2.VideoCapture(config["kamera"])


timer_verifikasi = config["timer_verifikasi"]  
encoding_path = os.path.join(current_directory,config["encoding_path"]) 
folder_wajah = os.path.join(current_directory,config["folder_wajah"])
faces_folder = os.path.join(current_directory,config["faces_folder"])
path_data = os.path.join(current_directory,config["path_data_th"])
timer = config["timer"] 
ports = serial.tools.list_ports.comports()
baud_rate = config["baudrate"]
threshold = config["threshold"]




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
            print("Mencoba port ", port_serial)
            ser = serial.Serial(port_serial, baud_rate,
                                        timeout=1, write_timeout=1)
            print(f"Terhubung ke {port_serial} dengan baud rate {baud_rate}")

            time.sleep(2)  # tunggu koneksi stabil
        except serial.SerialException as e:
            print(f"Gagal membuka port serial: {e}")
            while (1):
                pass

    elif pesan == "get_sensor\n":
        ser.write(pesan.encode())
        print("Mengirim permintaan sensor:", pesan)


    else:
        ser.write(pesan.encode())
        print("Mengirim pesan serial:", pesan.encode())



def web_wajah(message):
    global url_absen
    response = requests.get(url_absen+message)

    print(response)
    time.sleep(2)


def web_rfid(message):
    global url_absen
    response = requests.get(url_absen_rfid+message)

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
    print(url)
    respon = requests.get(url=url)
    print(respon.text)

    # Proses setiap orang dan simpan ke folder dummy
    for j , orang in enumerate(eval(respon.text)):
        id = orang["id"]
        nama = orang["nama"]
        rfid =  orang["rfid"]
        
        nama_data = id + "_" + nama + "_" +  rfid
        nama_folder_dummy = os.path.join(folder_dummy, nama_data)
        dictionary[nama_data] = j
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
    print(dictionary)
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

def get_confidences_from_folder(folder_path, max_images=100):
    conf_list = []
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.png'))]
    image_files = image_files[:max_images]

    for filename in image_files:
        path = os.path.join(folder_path, filename)
        img = cv2.imread(path)
        if img is None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5)

        for (x, y, w, h) in faces:
            roi = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(roi, FACE_SIZE)
            _, conf = recognizer.predict(face_resized)
            conf_list.append(conf)
            break  # Hanya ambil 1 wajah per gambar

    return conf_list


def encoding_wajah():
    global folder_wajah, encoding_path
    print("Mulai proses Encoding (perlu waktu tergantung jumlah foto)")
    proses_kirim_serial("@Encoding ... ")

    # Siapkan data
    images = []
    labels = []


    #TRAINING DAN SIMPAN

    for nama in os.listdir(folder_wajah):
     
        sub_folder = os.path.join(folder_wajah, nama)

        if os.path.isdir(sub_folder):
            for b in tqdm(os.listdir(sub_folder)):
                path_image = os.path.join(sub_folder, b)
                proses_kirim_serial("@Encoding ... ")
                if os.path.isfile(path_image):
                    frame = cv2.imread(path_image)

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.equalizeHist(gray)
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                    if len(faces) == 0:
                        print(f"⚠️  Tidak ditemukan wajah di: {nama}")
                        continue
                    # Cari wajah dengan ukuran (luas) terbesar
                    (x, y, w, h) = max(faces, key=lambda rect: rect[2] * rect[3])

                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0,200.20), 2)
                    cv2.putText(frame, nama, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,200.20), 2)
                    
                    face_roi = gray[y:y+h, x:x+w]
                    face_resized = cv2.resize(face_roi, FACE_SIZE)

                    images.append(face_resized)
                    labels.append(dictionary[nama])
                    print(f"✅ Tambah data: {nama} sebagai label {dictionary[nama]}")

                    
                            # Resize hasil crop untuk ditampilkan (tetap 480x480)
                    display_frame = cv2.resize(frame, (480, 480))
                    # cv2.imshow("Deteksi Wajah", display_frame)
                    # cv2.waitKey(500)


    proses_kirim_serial("@Training .. ")
    time.sleep(3)
    # recognizer.read(encoding_path)
    recognizer.train(images, np.array(labels))
    recognizer.save(encoding_path)
    print("\n✅ Training selesai! Model disimpan ke", encoding_path)
    
    print("Cek Treshold .... ")
    
    for nama in os.listdir(folder_wajah):
        sub_folder = os.path.join(folder_wajah, nama)
        # Ambil confidence dari dataset yang dikenal (min)
        conf_known = get_confidences_from_folder(sub_folder, max_images=10)
        # Ambil confidence dari wajah acak (max)
        conf_unknown = get_confidences_from_folder(faces_folder, max_images=100)
        proses_kirim_serial("@Encoding ... ")
        # Hitung rata-rata
        avg_min_conf = np.mean(conf_known) if conf_known else None
        avg_max_conf = np.mean(conf_unknown) if conf_unknown else None

        print(f"📉 Rata-rata confidence <{nama}> (dataset):", avg_min_conf)
        print(f"📈 Rata-rata confidence <{nama}> (tidak dikenal):", avg_max_conf)
        dictionary_threshold[nama] = [avg_min_conf,avg_max_conf]

    print("Simpan ... ")
    proses_kirim_serial("@Menyimpan")
    # Simpan ke file JSON
    with open(path_data, "w") as f:
        json.dump(dictionary_threshold, f, indent=4)


    # cv2.destroyAllWindows()

def inisiasi():
    global  folder_wajah,start_encoding, dictionary_threshold
    proses_kirim_serial("@"+"LOADING ... ")
    print(" >>>>>  Jika ada perubahan pada folder nama / foto, wajib menghapus file encoding_wajah.bin <<<<<  ")
    time.sleep(3)
    image_manager()

    


    if  start_encoding == 1 :
        print("perubahan data terdeteksi, membuat encoding baru ... ")
        try :
            os.remove(encoding_path)
        except:
            pass
        encoding_wajah()
        time.sleep(5)
        recognizer.read(encoding_path)

        start_encoding = 0

    try:
    #    coba load model
        recognizer.read(encoding_path)
        with open(path_data, "r") as f:
            dictionary_threshold = json.load(f)
        print("Load Model Sukses .. ")
      
    except:
        print("Gagal memuat data encoding sebelumnya, membuat file baru ...")
        encoding_wajah()

# Penyimpanan waktu tampil untuk tiap teks
active_texts = {}

def add_timed_text(text="normal", coord=(10, 10), duration_sec=5):
    global active_texts
    now = time.time()
    active_texts[text] = (now, duration_sec, coord)

def draw_active_texts(frame):
    global active_texts
    now = time.time()
    output_frame = frame.copy()

    for t, (start_time, dur, (x, y)) in list(active_texts.items()):
        if now - start_time <= dur:
            cv2.putText(output_frame, t, (x, y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 55), 2)
        else:
            del active_texts[t]

    return output_frame



def deteksi():
    global timer_start, timer_deteksi, elapsed_time, sekali_kirim, last_detected_name, timer_verifikasi, nama, id, threshold,last_rfid
    proses_kirim_serial("@Kamera Aktif")
    time.sleep(3)
    # Inisialisasi variabel
    timer_start = None
    timer_deteksi = 0
    elapsed_time = 0
    sekali_kirim = False
    last_detected_name = None
    last_rfid = None

    invers_dictionary  = {str(v): k for k, v in dictionary.items()}

    # cv2.namedWindow("Face Recognition", cv2.WINDOW_NORMAL)
    # cv2.resizeWindow("Face Recognition", 640, 480)
    # cv2.moveWindow("Face Recognition", 100, 100)

    while True:
        # Baca frame dari kamera
        res, frame = cam.read()
        nama_terdeteksi = None
 
        # Periksa apakah frame berhasil dibaca
        if not res:
                print("Error: Could not read frame.")
                break

############################################# YOLO ######################################################
   
        nama_terdeteksi = "Tidak Dikenali"
        nama = nama_terdeteksi
        
        id = ""
                     
        # Penyesuaian kontras dan kecerahan
      
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = cv2.equalizeHist(gray_frame)
        faces = face_cascade.detectMultiScale(gray_frame, 1.1, 5)

        # Cek kecocokan dengan data wajah yang dikenal
        
        for (x, y, w, h) in faces:
            face_roi = gray_frame[y:y+h, x:x+w]
            face_resized = cv2.resize(face_roi, FACE_SIZE)
            ukuran_wajah = w * h
            id_, conf = recognizer.predict(face_resized)

            
            nama_terdeteksi = invers_dictionary[str(id_)]
            threshold_min = dictionary_threshold[nama_terdeteksi][0]
            threshold_max = dictionary_threshold[nama_terdeteksi][1]
            proba = (threshold_max - conf )/ threshold_max * 100.0
            print(nama_terdeteksi, "max",threshold_max,"min",threshold_min,"th",threshold, "proba ", proba , "size ", ukuran_wajah )

            # semakin kecil conf semakin yakin
            
            if ukuran_wajah > 70000 :
                if proba >  threshold:
                    nama = nama_terdeteksi.split("_")[1]
                    id = nama_terdeteksi.split("_")[0]
                    
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 30), 2)
                    cv2.putText(frame, f"Nama {nama}", (x+w, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 30), 2)
                    cv2.putText(frame, f"id {id}", (x+w, y+20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 30), 2)
                    cv2.putText(frame, f"Data: {conf:.1f} ", (x+w, y+40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 30), 2)
                else :
                    nama_terdeteksi = "Tidak Dikenali"
                    proses_kirim_serial("@"+"Tidak DIkenali")
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (5, 0, 255), 2)
                    
            elif ukuran_wajah < 70000 :
                nama_terdeteksi = "Tidak Dikenali"
                proses_kirim_serial("@"+"LEBIH DEKAT .. ")
                cv2.rectangle(frame, (x, y), (x+w, y+h), (5, 0, 255), 2)
                cv2.putText(frame, f"Berdiri lebih dekat ", (x, y+h+20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (5, 0, 255), 2)
                    
                
            break

        # Tampilkan nama di frame
        cv2.putText(frame, nama, (0, 400),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, id, (0, 450),
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
                    proses_kirim_serial("@"+nama) # untuk tampil nama di lcd
                    proses_kirim_serial("#"+nama) # untuk buka pintu tanpa buzzer
                    sekali_kirim = True
                    cv2.putText(frame, "MENGIRIM ABSEN ...", (0, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                    web_wajah(id)

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
                if remaining_time != 0 :
                    proses_kirim_serial("@Tunggu :"+str(round(remaining_time, 1))+"s")

############################################# RFID ######################################################


        # dapatkan rfid
        kode_rfid = ""
        kode_rfid = ser.readline().decode('utf-8', errors='ignore').strip()
        print("kode_rfid : ",kode_rfid,type(kode_rfid),len(kode_rfid))
        
        status = 0
        if kode_rfid != "" :
                print("D:",dictionary)
                for k in (dictionary.keys()):
                    data = k.split("_")
                    
                    if data[2] == kode_rfid :
                        # kirim ke server
                        
                        proses_kirim_serial("get_sensor")
                        time.sleep(3)
                        proses_kirim_serial("@"+data[1])
                        
                        proses_kirim_serial("!"+data[1]) # untuk buka pindu dan buzzer aktif
                        print("BENAR")
                        add_timed_text( "ID : " + data[2], (0, 300))
                        add_timed_text( "NAMA : " + data[1], (0, 330))
                        add_timed_text("MENGIRIM ABSEN ...", (0, 360))
                        web_rfid(data[2])
                        
                    
                        break

                    status += 1
            
                if status == len(dictionary.keys()) : 
                    #  proses_kirim_serial("@"+data[1])
                    time.sleep(3)
                    proses_kirim_serial("@Tidak Terdaftar")
                    add_timed_text( "ID : " + kode_rfid, (0, 300))
                    add_timed_text("Tidak Terdaftar", (0, 330))
           

        # Tampilkan frame
        frame = draw_active_texts(frame)
        # cv2.imshow("Face Recognition", frame)

        # Tombol keluar
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Bersihkan sumber daya
    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    proses_kirim_serial("inisiasi")
    inisiasi()
    deteksi()
