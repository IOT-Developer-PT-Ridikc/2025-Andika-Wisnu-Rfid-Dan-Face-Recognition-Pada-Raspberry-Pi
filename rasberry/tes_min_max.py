import cv2
import os
import numpy as np

# Parameter
FACE_SIZE = (100, 100)  # Sesuaikan dengan ukuran saat training
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
MODEL_PATH = "d:/PTRIDIKC/clone_github/2025-Andika-restu-Rfid-Dan-Face-Recognition-Pada-Raspberry-Pi/rasberry/encoding_wajah.bin"
FOLDER_A = "d:/PTRIDIKC/clone_github/2025-Andika-restu-Rfid-Dan-Face-Recognition-Pada-Raspberry-Pi/rasberry/dataset_wajah/IDE20250714035341492_bimo_0213BC02"  # Gambar wajah yang dikenal
FOLDER_B = "d:/PTRIDIKC/clone_github/2025-Andika-restu-Rfid-Dan-Face-Recognition-Pada-Raspberry-Pi/rasberry/faces.v1i.yolov8/train/images"  # Gambar wajah acak

# Load model dan cascade
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

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

# Ambil confidence dari dataset yang dikenal (min)
conf_known = get_confidences_from_folder(FOLDER_A, max_images=10)
# Ambil confidence dari wajah acak (max)
conf_unknown = get_confidences_from_folder(FOLDER_B, max_images=10)

# Hitung rata-rata
avg_min_conf = np.mean(conf_known) if conf_known else None
avg_max_conf = np.mean(conf_unknown) if conf_unknown else None

print("📉 Rata-rata confidence (dataset A / dikenal):", avg_min_conf)
print("📈 Rata-rata confidence (dataset B / tidak dikenal):", avg_max_conf)
