from flask import Flask, request, Response
from threading import Lock, Thread
import cv2
import numpy as np
import socket
import time

app = Flask(__name__)
current_frame = None
lock = Lock()

@app.route('/upload_frame', methods=['POST'])
def upload_frame():
    global current_frame
    file = request.files['frame']
    if file:
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        with lock:
            current_frame = frame
    return 'OK'

@app.route('/video')
def video():
    def generate():
        while True:
            with lock:
                if current_frame is None:
                    continue
                _, buffer = cv2.imencode('.jpg', current_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cek')
def cek():
    return 'SERVER_FLASK_OK'

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def show_frame():
    global current_frame
    while True:
        with lock:
            frame = current_frame.copy() if current_frame is not None else None
        if frame is not None:
            cv2.imshow("Gambar Diterima", frame)
            # proses tambahan di sini, misal deteksi wajah
            if cv2.waitKey(1) & 0xFF == 27:  # Tekan ESC untuk keluar
                break
        else:
            time.sleep(0.05)  # hindari CPU usage tinggi
    cv2.destroyAllWindows()

if __name__ == '__main__':
    ip = get_ip()
    print(f"✅ Flask server siap di: http://{ip}:5000")

    # Jalankan thread untuk imshow
    Thread(target=show_frame, daemon=True).start()

    # Jalankan Flask
    app.run(host='0.0.0.0', port=5000)
