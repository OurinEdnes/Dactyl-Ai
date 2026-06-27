import cv2
import mediapipe as mp
import csv
import os

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=2, 
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

csv_path = "Data/dataset_bimanual.csv"

# --- 1. MEMBUAT HEADER UNTUK 126 FITUR (KIRI + KANAN) ---
header = ['label']
# Bikin header tangan kiri (63 kolom)
for i in range(21): header.extend([f'L_x{i}', f'L_y{i}', f'L_z{i}'])
# Bikin header tangan kanan (63 kolom)
for i in range(21): header.extend([f'R_x{i}', f'R_y{i}', f'R_z{i}'])

if not os.path.exists(csv_path):
    os.makedirs('Data', exist_ok=True)
    with open(csv_path, mode='w', newline='') as f:
        csv.writer(f).writerow(header)

print("Bimanual System Ready!")
print("=========================================")
print("TIPS REKAM DATA (Tahan tombol di keyboard saat pose):")
print("[0] : Telunjuk Lurus (Move)")
print("[1] : Cubit (Klik)")
print("[2] : Megang Bola / C-Shape (Volume/Bright)")
print("[3] : Peace (Keyboard)")
print("[4] : Frame Kamera (Screenshot)")
print("[5] : Dua Jari Lurus Ninja (Scroll)")
print("[6] : Tangan Terbuka Kertas (Swipe Kiri/Kanan)")
print("[7] : Tangan Mengepal Kuat (Standby/Pause)")
print("[Q] : Keluar Program")
print("=========================================")

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    # Balik gambar agar seperti cermin
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    # Siapkan array kosong berisi nol (0.0) untuk jaga-jaga kalau tangan gak kelihatan
    left_hand_data = [0.0] * 63
    right_hand_data = [0.0] * 63
    hand_detected = False

    if result.multi_hand_landmarks and result.multi_handedness:
        hand_detected = True
        # Looping setiap tangan yang terdeteksi di layar
        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Cek ini tangan kiri atau kanan
            # Note: Karena kita pakai cv2.flip (efek cermin), label MediaPipe kebalik!
            # Jadi kalau MP bilang 'Left', itu fisiknya adalah Tangan Kanan Ourin.
            mp_label = result.multi_handedness[idx].classification[0].label
            hand_label = 'Right' if mp_label == 'Left' else 'Left'
            
            # --- TAMBAHAN UI: Tulis teks Kiri/Kanan di pergelangan tangan biar akurat! ---
            wrist_x = int(hand_landmarks.landmark[0].x * frame.shape[1])
            wrist_y = int(hand_landmarks.landmark[0].y * frame.shape[0])
            cv2.putText(frame, f"Tangan {hand_label}", (wrist_x - 30, wrist_y - 20), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 2)
            
            # Ekstrak 21 koordinat
            coords = []
            for lm in hand_landmarks.landmark:
                coords.extend([lm.x, lm.y, lm.z])
                
            # Masukkan ke array yang sesuai
            if hand_label == 'Left':
                left_hand_data = coords
            elif hand_label == 'Right':
                right_hand_data = coords

    # Tampilkan panduan di layar
    cv2.putText(frame, "Tahan [0-7] utk rekam, [Q] utk keluar", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.imshow("Kamera Pengumpul Data V2", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
        
    # --- LOGIKA PENYIMPANAN DATA ---
    # Kalau tombol 0 sampai 7 ditekan dan minimal ada 1 tangan di layar
    elif key >= ord('0') and key <= ord('7') and hand_detected:
        label = chr(key)
        
        # Gabungkan data: Label + Data Kiri + Data Kanan (Total 127 item)
        row_data = [label] + left_hand_data + right_hand_data
        
        with open(csv_path, mode='a', newline='') as f:
            csv.writer(f).writerow(row_data)
            
        print(f"Data Tersimpan! (Label: {label})")

cap.release()
cv2.destroyAllWindows()
print("Selesai ngerekam!")