# LIBRARY FACE RECOGNITION KHUSUS RASBERRY (PENGGUNAAN RAM 500MB)



import cv2
import numpy as np
import os
import psutil

# Parameter
DATASET_DIR = "d:/PTRIDIKC/clone_github/2025-Andika-restu-Rfid-Dan-Face-Recognition-Pada-Raspberry-Pi/rasberry/data"  # Folder berisi gambar terstruktur per orang
MODEL_PATH = "trained_model.yml"
FACE_SIZE = (200, 200)

# Inisialisasi detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Siapkan data
images = []
labels = []

for label_name in os.listdir(DATASET_DIR):
    label_path = os.path.join(DATASET_DIR, label_name)
    if not os.path.isdir(label_path):
        continue
    label = int(label_name)
    for filename in os.listdir(label_path):
        file_path = os.path.join(label_path, filename)
        img = cv2.imread(file_path)
        if img is None:
            print(f"❌ Gagal baca: {file_path}")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            print(f"⚠️  Tidak ditemukan wajah di: {file_path}")
            continue

        (x, y, w, h) = faces[0]  # Ambil wajah pertama saja
        face_roi = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, FACE_SIZE)

        images.append(face_resized)
        labels.append(label)
        print(f"✅ Tambah data: {file_path} sebagai label {label}")

# Latih model LBPH
recognizer = cv2.face.LBPHFaceRecognizer_create(
    radius=2,
    neighbors=8,
    grid_x=50,
    grid_y=50
   
)

recognizer.train(images, np.array(labels))
recognizer.save(MODEL_PATH)
print("\n✅ Training selesai! Model disimpan ke", MODEL_PATH)

# recognizer = cv2.face.LBPHFaceRecognizer_create()
# recognizer.read(MODEL_PATH)


# Mulai kamera untuk uji
print("🎥 Mulai kamera untuk uji model...")
cap = cv2.VideoCapture(0)
cv2.namedWindow("Face Recognition", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Face Recognition", 640, 480)
cv2.moveWindow("Face Recognition", 100, 100)

recognizer.read(MODEL_PATH)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_frame = cv2.equalizeHist(gray_frame)
    faces = face_cascade.detectMultiScale(gray_frame, 1.1, 5)

    for (x, y, w, h) in faces:
        face_roi = gray_frame[y:y+h, x:x+w]
        face_resized = cv2.resize(face_roi, FACE_SIZE)

        id_, conf = recognizer.predict(face_resized)


        text = f"ID: {id_} ({int(conf)})"
        color = (0, 255, 0) if conf < 8600 else (0, 0, 255) # batas deteksi
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.putText(frame, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        # Ambil penggunaan RAM oleh proses saat ini
        process = psutil.Process(os.getpid())
        ram_usage = process.memory_info().rss / (1024 * 1024)  # dalam MB

        # Tampilkan di pojok kiri atas frame
        cv2.putText(frame, f"RAM: {ram_usage:.1f} MB", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)


    cv2.imshow("Face Recognition", frame)
    key = cv2.waitKey(1)
    if key == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
