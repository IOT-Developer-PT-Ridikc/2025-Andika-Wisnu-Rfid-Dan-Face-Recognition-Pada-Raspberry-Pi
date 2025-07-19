import cv2
import requests
import socket
import time
from concurrent.futures import ThreadPoolExecutor
import json
import serial
import serial.tools.list_ports
from datetime import datetime
from datetime import date
import time
import os
import ast

ip = ""
nama_terdeteksi = ""
id_terdeteksi = ""
status = ""
kode_rfid = ""

# Mendapatkan folder saat ini
current_directory = os.path.dirname(os.path.abspath(__file__))

print("Tanggal :", str(date.today()))
print("Folder saat ini:", current_directory)
# rasberry gak bisa cari port otomatis
port_serial = "/dev/ttyUSB0"
# port_serial = "COM7"

# Default config
config_path = os.path.join(current_directory, 'config.json')
default_config = {
    "kamera": 0,
    "port_serial": port_serial, 
    "baudrate": 9600,
}

# Cek dan buat file config jika belum ada
if not os.path.exists(config_path):
    with open(config_path, 'w') as file:
        json.dump(default_config, file, indent=4)

# Baca config
with open(config_path, 'r') as file:
    config = json.load(file)

# Open the camera
cap = cv2.VideoCapture(config["kamera"])
port_serial = config["port_serial"]
baud_rate = config["baudrate"]


# Check if the camera is opened successfully

if not cap.isOpened():
    while (1):
        print("Error: Could not open camera.")
        print("Periksa nomor kamera / sambungan kamera ... ")
        time.sleep(1)
else:
    print("Camera opened successfully.")

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


def kirim_rfid(text):
    data = {'text': text}
    res = requests.post(f'http://{ip}:5000/rfid', data=data)
    print(res.text)

def get_base_ip():
    global ip
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return '.'.join(ip.split('.')[:-1])  # contoh: 192.168.1

def cari_server_flask():
    base_ip = get_base_ip()
    kandidat_ip = [f"{base_ip}.{i}" for i in range(1, 255)]

    def cek(ip):
        try:
            r = requests.get(f"http://{ip}:5000/cek", timeout=0.5)
            if r.text.strip() == 'SERVER_FLASK_OK':
                print(f"🟢 Server Flask ditemukan: {ip}")
                return ip
        except:
            return None

    with ThreadPoolExecutor(max_workers=50) as ex:
        hasil = ex.map(cek, kandidat_ip)

    hasil_valid = [ip for ip in hasil if ip]
    return hasil_valid[0] if hasil_valid else None


def kamera(server_ip):
    ret, frame = cap.read()      
    _, img_encoded = cv2.imencode('.jpg', frame)

    try:
        r = requests.post(f"http://{server_ip}:5000/upload_frame", files={'frame': img_encoded.tobytes()})
        if r.status_code != 200:
                print("⚠️ Upload gagal:", r.status_code)
    except Exception as e:
        print("❌ Gagal kirim:", e)

# LOGIKA UTAMA
def kirim_gambar(server_ip):
    global id_terdeteksi,nama_terdeteksi,status, kode_rfid
    while True:
        kamera(server_ip)
        proses_kirim_serial("get_sensor")
        kode_rfid = ser.readline().decode('utf-8', errors='ignore').strip()
        kirim_rfid(kode_rfid)
        if kode_rfid != "":
            proses_kirim_serial("@ID:"+kode_rfid)
            
            time.sleep(4)
        
        data = requests.get(f"http://{server_ip}:5000/id_nama").text
        id_terdeteksi,nama_terdeteksi =  ast.literal_eval(data)
        status = requests.get(f"http://{server_ip}:5000/status").text
        print("data : ")
        print("rfid :",kode_rfid)
        print("id:",id_terdeteksi)
        print("nama:",nama_terdeteksi)
        print("status : ",status)

        
        # manajemen pensan_status
        list_status = status.split(",")

        if status != "":
            if len(list_status) < 2 :
                # hanya tamplilan
                proses_kirim_serial("@"+status)
            else :
                #kontrol dan tampilan
                if list_status[-1] == "0":
                    proses_kirim_serial("#"+list_status[1]) # tanpa buzzer
                elif list_status[-1] == "1":
                    proses_kirim_serial("!"+list_status[1]) # dengan buzzer
        


if __name__ == '__main__':
    proses_kirim_serial("inisiasi")
    print("🔍 Mencari server Flask...")
    ip_server = cari_server_flask()
    if ip_server:
        print("📡 Mengirim gambar ke:", ip_server)
        kirim_gambar(ip_server)
    else:
        print("❌ Tidak ditemukan server Flask.")
