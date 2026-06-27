import cv2
import mediapipe as mp
import pyautogui
import pickle
import numpy as np
import os

# =======================================================
# 🦈 SCRIPT INTEGRASI KURSOR MAGIC OURIN 🦈
# =======================================================

# Load Otak AI
model_path = 'models/svm_gesture_model.pkl'
if not os.path.exists(model_path):
    print("❌ Model tidak ditemukan! Latih dulu di train_model.py ya!")
    exit()

# Membuka file model & scaler
with open(model_path, 'rb') as f:
    data = pickle.load(f)
    model = data['model']
    scaler = data['scaler']

# Setup MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

# Setting PyAutoGUI
pyautogui.FAILSAFE = True # Geser kursor ke pojok kiri atas layar buat matiin program
pyautogui.PAUSE = 0.01 

cap = cv2.VideoCapture(0)

print("🦈 Sistem Kursor Magic Siap! Tekan 'q' untuk keluar.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    # Mirroring & Proses MediaPipe
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Mengambil koordinat (X, Y, Z) dari 21 titik = 63 koordinat
            # Karena data training pakai 126 (2 tangan), kita isi tangan kedua dengan 0
            coords = []
            for lm in hand_landmarks.landmark:
                coords.extend([lm.x, lm.y, lm.z])
            
            # Tambahkan 63 angka nol untuk padding tangan kedua
            coords.extend([0] * 63)
            
            # Prediksi dengan Model SVM
            input_data = np.array(coords).reshape(1, -1)
            input_scaled = scaler.transform(input_data)
            prediction = model.predict(input_scaled)
            gesture = int(prediction[0])

            # Tampilan visual di layar
            cv2.putText(frame, f"Gestur AI: {gesture}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # LOGIKA KONTROL (Sesuaikan dengan label angka yang Ourin buat)
            # Contoh: 0 = Bergerak, 1 = Klik
            if gesture == 0: 
                # Gerakin kursor
                x = int(hand_landmarks.landmark[8].x * pyautogui.size().width)
                y = int(hand_landmarks.landmark[8].y * pyautogui.size().height)
                pyautogui.moveTo(x, y)
            
            elif gesture == 1: 
                # Klik kiri
                pyautogui.click()
                pyautogui.sleep(0.5) # Jeda biar nggak spam klik

    cv2.imshow('Magic Cursor - Aikoo', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()