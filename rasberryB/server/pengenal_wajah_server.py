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
    from datetime import datetime
    from datetime import date
    from flask import Flask, request, Response
    from threading import Lock, Thread
    import socket
    import time

except ImportError:
    print("Library tidak ditemukan, menginstal sekarang...")
    os.system("pip install numpy==1.24.3 face_recognition==1.3.0 tqdm==4.67.0 pickle-mixin==1.0.2 opencv-python==4.10.0.84 ultralytics==8.3.32 requests==2.32.3 keyboard==0.13.5")

    from tqdm import tqdm
    import pickle
    import cv2
    from ultralytics import YOLO
    import numpy as np
    import face_recognition  # Coba impor kembali setelah instalasi
    import json
    from datetime import datetime
    from datetime import date
    from flask import Flask, request, Response
    from threading import Lock, Thread
    import socket
    import time

# Inisialisasi timer
timer_start = None
timer1 = 0
timer2 = 0
timer3 = 0
nama_terdeteksi = ""
id_terdeteksi = ""
kode_rfid = ""
last_kode_rfid = ""
status_rfid = 0
sekali_kirim = 0
sekali_kirim_rfid = 0
elapsed_time = 0
remaining_time = 0
start_encoding = 0

pesan_status = ""


# Mendapatkan folder saat ini
current_directory = os.path.dirname(os.path.abspath(__file__))

print("Tanggal :", str(date.today()))
print("Folder saat ini:", current_directory)

#######################################################################
# Default config
config_path = os.path.join(current_directory, "config.json")
default_config = {
    "timer_verifikasi": 5,  # Timer countdown dalam detik
    "folder_wajah": "dataset_wajah",
    "model_yolo": "model_yolov8.pt",
    "toleransi": 0.5,  # semakin kecil semakin detail perbedaan wajah, tapi sensitifitas berkurang,
    "timer": 5,  # absensi dimulai setelah wajah terdeteksi selama 5 detik
    "encoding_path": "encoding_wajah.bin",
}

########################################################################
# jangan diubah, jgn dihapus
url = "https://localhost.scode.web.id/2025-andika-restu-monitoring-akses-pintu/api/api.php"
url_absen = url + "?id_wajah="
url_absen_rfid = url + "?rfid="

# Cek dan buat file config jika belum ada
if not os.path.exists(config_path):
    with open(config_path, "w") as file:
        json.dump(default_config, file, indent=4)

# Baca config
with open(config_path, "r") as file:
    config = json.load(file)

data_dataset = []
data_semua = {}
data_nama = []
status_nama = []
konfirmasi_nama = []
# Load YOLO model
yolo_model = YOLO(os.path.join(current_directory,config["model_yolo"]))
timer_verifikasi = config["timer_verifikasi"]
folder_wajah = os.path.join(current_directory,config["folder_wajah"])
toleransi = config["toleransi"]
timer = config["timer"]
encoding_path = os.path.join(current_directory, config["encoding_path"])
# Check data terbaru


def web_wajah(message):
    global url_absen
    response = requests.get(url_absen + message)

    print(response)



def web_rfid(message):
    global url_absen
    response = requests.get(url_absen_rfid + message)

    print(response)
   


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
    for orang in eval(respon.text):
        id_terdeteksi = orang["id"]
        nama_terdeteksi = orang["nama"]
        rfid = orang["rfid"]

        nama_folder_dummy = os.path.join(folder_dummy, id_terdeteksi + "_" + nama_terdeteksi + "_" + rfid)
        os.makedirs(nama_folder_dummy, exist_ok=True)
        os.makedirs(folder_wajah, exist_ok=True)

        for i in range(10):
            url_gambar = orang["foto" + str(i + 1)]
            url_gambar = url_gambar.replace("\\", "").replace("////", "//")
            print("URL : ", url_gambar)

            try:
                gambar_respon = requests.get(url_gambar)
                if gambar_respon.status_code == 200:
                    path_dummy = os.path.join(nama_folder_dummy, nama_terdeteksi + "_" + str(i + 1) + ".jpg")
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

    list_dummy = os.listdir(folder_dummy)
    list_data = os.listdir(folder_wajah)
    

    if ukuran_dummy != ukuran_wajah or list_dummy != list_data:
        print("Data berubah, mengganti isi folder wajah")
        start_encoding = 1
        # Hapus semua isi folder wajah
        try :
            shutil.rmtree(folder_wajah)
        except:
            pass

        os.makedirs(folder_wajah, exist_ok=True)
        if os.path.exists(folder_wajah):
            shutil.rmtree(folder_wajah)
            


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

    for nama_terdeteksi in os.listdir(folder_wajah):
        poto = []
        sub_folder = os.path.join(folder_wajah, nama_terdeteksi)

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

                            for top, right, bottom, left in face_locations:
                                # Gambar kotak wajah dari face_recognition (biru)
                                cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)

                            # Resize hasil crop untuk ditampilkan (tetap 480x480)
                            display_frame = cv2.resize(frame, (480, 480))
                            cv2.imshow("Deteksi Wajah", display_frame)
                            cv2.waitKey(500)

                            if face_encodings:
                                poto.append(face_encodings[0])

        if poto:
            data_semua[nama_terdeteksi] = poto
            print(f"{nama_terdeteksi} selesai.")
        else:
            print("WAJAH TIDAK ADA PADA GAMBAR.")
            while True:
                pass

    with open(encoding_path, "wb") as f:
        pickle.dump(data_semua, f)
    print("Data encoding disimpan dalam file encoding_wajah.bin")
    cv2.destroyAllWindows()


def inisiasi():
    global data_semua, data_nama, folder_wajah, start_encoding
    global timer_start, timer_deteksi, elapsed_time, sekali_kirim, last_detected_name, timer_verifikasi, nama_terdeteksi, id_terdeteksi, data_nama, last_rfid

    # Inisialisasi variabel
    timer_start = None
    timer_deteksi = 0
    elapsed_time = 0
    sekali_kirim = False
    last_detected_name = None
    last_rfid = None
    print(" >>>>>  Jika ada perubahan pada folder nama_terdeteksi / foto, wajib menghapus file encoding_wajah.bin <<<<<  ")
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
        print("Data nama_terdeteksi : ", data_nama)
        start_encoding = 0

    for l in data_nama:
        status_nama.append(0)
        konfirmasi_nama.append(0)


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
            cv2.putText(output_frame, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 55), 2)
        else:
            del active_texts[t]

    return output_frame


def deteksi(frame):
    global nama_rfid,sekali_kirim_rfid, pesan_status,status_rfid, kode_rfid, timer_start, timer_deteksi, elapsed_time, sekali_kirim, last_detected_name, timer_verifikasi, nama_terdeteksi, id_terdeteksi, last_rfid, data_nama
    ############################################# RFID ######################################################

    status = []
    if kode_rfid != "":
        # cv2.putText(frame, kode_rfid, (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        nama_rfid = ""
        if sekali_kirim_rfid == 0:
            for k in data_nama:
                data = k.split("_")
                # print("data", data)
                if data[2] == kode_rfid:
                    # kirim ke server
                    nama_rfid = data[1]
                    pesan_status = data[2] + "," + data[1] + ",1"  # buzzer
                    print("BENAR")
                    add_timed_text("ID : " + data[2], (0, 300))
                    add_timed_text("NAMA : " + data[1], (0, 330))
                    add_timed_text("MENGIRIM ABSEN ...", (0, 360))
                    web_rfid(data[2])
                    

                    break
                status.append(False)
            sekali_kirim_rfid = 1

        if len(status) == len(data_nama):
            pesan_status = "Tidak Terdaftar,Tidak Terdaftar,2"  # untuk buzzer panjang

            add_timed_text("ID : " + kode_rfid, (0, 300))
            add_timed_text("Tidak Terdaftar", (0, 330))
        
        status_rfid = 0
        
        
           

    # Tampilkan frame
    frame = draw_active_texts(frame)
    ############################################# YOLO ######################################################
    # Jalankan YOLO untuk deteksi
    if kode_rfid == "" :
        sekali_kirim_rfid = 0
        results = yolo_model(frame)

        # Loop setiap hasil deteksi

        nama_terdeteksi = "Tidak Dikenal"
        id_terdeteksi = ""
       
        face = 0
      
        for r in results:
           
            boxes = r.boxes.xyxy.tolist()
            
            for box in boxes:
                face += 1
                # Ekstraksi koordinat bounding box
                x1, y1, x2, y2 = map(int, box[:4])

                # Potong dan proses gambar untuk pengenalan wajah
                if y1 >= 20:
                    image_rgb = frame[y1 - 20 : y2, x1:x2]
                    cv2.rectangle(frame, (x1, y1 - 20), (x2, y2), (0, 255, 0), 2)
                else:
                    image_rgb = frame[y1:y2, x1:x2]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Penyesuaian kontras dan kecerahan
                alpha = 1.5
                beta = 20
                image_rgb = cv2.convertScaleAbs(image_rgb, alpha=alpha, beta=beta)

                input_face_encodings = face_recognition.face_encodings(image_rgb)

                koordinat = 0
                # Cek kecocokan dengan data wajah yang dikenal
                for k in data_nama:
                    konfirmasi_nama[data_nama.index(k)] = 0
                    for l in data_semua[k]:
                        matches = face_recognition.compare_faces([l], input_face_encodings[0], tolerance=toleransi) if input_face_encodings else []
                        if True in matches:
                            konfirmasi_nama[data_nama.index(k)] += 1

                    koordinat += 10

                    probabilitas = konfirmasi_nama[data_nama.index(k)] / len(data_semua[k]) * 100
                    print("Probabilitas : ", k, probabilitas, "%")
                    # Tampilkan nama_terdeteksi di frame
                    cv2.putText(frame, k.split("_")[1] + " " + str(round(probabilitas, 1)) + "%", (0, 60 + koordinat * 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

                    nama_orang = ""
                    if konfirmasi_nama[np.argmax(konfirmasi_nama)] != 0:
                        nama_orang = data_nama[np.argmax(konfirmasi_nama)]

                    try:
                        nama_terdeteksi = nama_orang.split("_")[1]
                        id_terdeteksi = nama_orang.split("_")[0]
                    except:
                        pass
                        

                # Tampilkan nama_terdeteksi di frame
                cv2.putText(frame, nama_terdeteksi, (x1, y1 - 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, id_terdeteksi, (x1, y1 - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Logika Timer
        if nama_terdeteksi != "Tidak Dikenal":
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
                pesan_status = id_terdeteksi + "," + nama_terdeteksi + ",0"  # untuk tampil nama_terdeteksi di lcd
                sekali_kirim = True
                cv2.putText(frame, "MENGIRIM ABSEN ...", (0, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                web_wajah(id_terdeteksi)
                

        else:
            # Reset jika tidak ada nama_terdeteksi yang terdeteksi
            timer_start = None
            elapsed_time = 0
            sekali_kirim = False
            last_detected_name = None
            if face == 0 :
                pesan_status = "Terhubung"
            else :
                pesan_status = "Tidak Dikenal"

        # Tampilkan timer di frame
        if timer_start:
            cv2.putText(frame, f"Status : ({round(remaining_time, 1)}s)", (0, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            if remaining_time > 0:
                pesan_status = f"Tunggu : ({round(remaining_time, 1)}s)"
          
    return frame


####                    BAGIAN SERVER
app = Flask(__name__)
current_frame = None
lock = Lock()


@app.route("/upload_frame", methods=["POST"])
def upload_frame():
    global kode_rfid, current_frame, status_rfid, timer3
    # Ambil RFID

    
    data = request.form.get("text", None)
        
    if data and status_rfid == 0:
            print(f"📟 RFID diterima: {kode_rfid}")
            print("status : ",pesan_status)
            kode_rfid = data
            status_rfid = 1
            
    else:
            print("⚠️ Tidak ada RFID dikirim")
            kode_rfid = ""
        

    file = request.files["frame"]
    if file:
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        with lock:
            current_frame = frame
    return "OK"


@app.route("/video")
def video():
    def generate():
        while True:
            with lock:
                if current_frame is None:
                    continue
                _, buffer = cv2.imencode(".jpg", current_frame)
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/cek")
def cek():
    return "SERVER_FLASK_OK"


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()


# untuk kasih nama dan id ke rasberry
@app.route("/id_nama", methods=["GET"])
def id_nama():
    global id_terdeteksi, nama_terdeteksi
    try:
        return str([id_terdeteksi, nama_terdeteksi])
    except:
        return "failed name updated", 400


# untuk kontrol semuanya
@app.route("/status", methods=["GET"])
def status():
    global pesan_status
    try:
        current_pesan = str(pesan_status)
        pesan_status = ""
        return current_pesan
    except:
        return "failed status updated", 400
     


def show_frame():
    global current_frame
    while True:
        with lock:
            frame = current_frame.copy() if current_frame is not None else None
        if frame is not None:
            frame = deteksi(frame)
            cv2.imshow("Gambar Diterima", frame)
            # proses tambahan di sini, misal deteksi wajah
            if cv2.waitKey(1) & 0xFF == 27:  # Tekan ESC untuk keluar
                break
        else:
            time.sleep(0.05)  # hindari CPU usage tinggi
    cv2.destroyAllWindows()


if __name__ == "__main__":
    inisiasi()
    ip = get_ip()
    print(f"✅ Flask server siap di: http://{ip}:5000")
    print("Menunggu Koneksi Rasberry .... ")

    # Jalankan thread untuk imshow
    Thread(target=show_frame, daemon=True).start()

    # Jalankan Flask
    app.run(host="0.0.0.0", port=5000)
