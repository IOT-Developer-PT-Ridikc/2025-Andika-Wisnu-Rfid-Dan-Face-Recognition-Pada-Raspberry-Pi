import cv2
import requests
import socket
import time
from concurrent.futures import ThreadPoolExecutor
ip = ""


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

def kirim_gambar(server_ip):
    cap = cv2.VideoCapture(0)
    a = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        a = a + 1
        if a % 10 == 0 :
            kirim_rfid(str(a))
            
        _, img_encoded = cv2.imencode('.jpg', frame)
        try:
            r = requests.post(f"http://{server_ip}:5000/upload_frame", files={'frame': img_encoded.tobytes()})
            if r.status_code != 200:
                print("⚠️ Upload gagal:", r.status_code)
        except Exception as e:
            print("❌ Gagal kirim:", e)
            break
        time.sleep(0.1)


if __name__ == '__main__':
    print("🔍 Mencari server Flask...")
    ip_server = cari_server_flask()
    if ip_server:
        print("📡 Mengirim gambar ke:", ip_server)
        kirim_gambar(ip_server)
    else:
        print("❌ Tidak ditemukan server Flask.")
