import cv2
import mediapipe as mp
import pyautogui
import pickle
import numpy as np
import os
import ctypes
from ctypes import wintypes


# Setup MediaPipe Hands (Mendukung 2 tangan secara simultan)
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=2, 
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# State Sistem & Manajemen Kunci (Inisialisasi Variabel Kritis)
is_paused = False
keyboard_active = False
is_dragging = False
pinch_start_time = None

# Konfigurasi Pengamanan OS PyAutoGUI (Failsafe & Zero-Delay)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0

# Cooldown & Timer State
last_click_time = 0.0
last_click_type = None
last_swipe_time = 0.0
last_typed_time = 0.0
last_pause_toggle_time = 0.0
last_keyboard_toggle_time = 0.0
keyboard_toggle_start = None
pause_toggle_start = None
screenshot_start = None
flash_frames = 0
screenshot_cooldown = 0.0

# Posisi Koordinat Sebelumnya (untuk Deteksi Delta/Rotasi/Scroll)
prev_right_angle = None
prev_left_angle = None
prev_scroll_x = None
prev_scroll_y = None

import math
import time
import subprocess
import threading


# Load Otak AI
model_path = 'models/svm_gesture_model.pkl'
if not os.path.exists(model_path):
    print("[ERROR] Model tidak ditemukan! Latih dulu di train_model.py ya!")
    exit()

# Membuka file model & scaler
with open(model_path, 'rb') as f:
    data = pickle.load(f)
    model = data['model']
    scaler = data['scaler']

# Filter Smoothing EMA untuk Kursor
cursor_x, cursor_y = 0.5, 0.5
alpha = 0.25  # Semakin kecil semakin mulus, tapi sedikit ada delay

# History Gerakan Swipe (Tangan Kiri)
left_x_history = []
left_time_history = []

# Status Kecerahan Layar (PowerShell Asynchronous)
current_brightness = 50
brightness_thread_running = False

def change_brightness(delta):
    global current_brightness, brightness_thread_running
    if brightness_thread_running:
        return
    current_brightness = max(0, min(100, current_brightness + delta))
    brightness_thread_running = True
    
    def run():
        global brightness_thread_running
        # Gunakan PowerShell WmiSetBrightness agar tidak menghambat frame kamera
        cmd = f"powershell -Command \"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {current_brightness})\""
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        brightness_thread_running = False
        
    threading.Thread(target=run, daemon=True).start()

# Definisikan Layout Keyboard Hantu (10 kolom per baris)
keys_row1 = ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P']
keys_row2 = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Back']
keys_row3 = ['Z', 'X', 'C', 'V', 'B', 'N', 'M', 'Space', 'Enter', 'Close']

keyboard_keys = []
# Row 1 (Y: 460 - 530)
for idx, char in enumerate(keys_row1):
    x1 = 100 + idx * 108
    keyboard_keys.append({'key': char, 'x1': x1, 'y1': 460, 'x2': x1 + 100, 'y2': 530})
# Row 2 (Y: 540 - 610)
for idx, char in enumerate(keys_row2):
    x1 = 100 + idx * 108
    keyboard_keys.append({'key': char, 'x1': x1, 'y1': 540, 'x2': x1 + 100, 'y2': 610})
# Row 3 (Y: 620 - 690)
for idx, char in enumerate(keys_row3):
    x1 = 100 + idx * 108
    keyboard_keys.append({'key': char, 'x1': x1, 'y1': 620, 'x2': x1 + 100, 'y2': 690})

# Pencatat hover tombol keyboard virtual
hover_start = {}

def calculate_distance(p1, p2):
    # Menggunakan Jarak Euclidean 2D (X, Y) karena jauh lebih akurat dan stabil pada koordinat kamera 2D
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

# Jalankan Kamera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

window_name = 'Magic Cursor - Aikoo'
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
window_setup_done = False
cached_hwnd = None

def init_win32_argtypes():
    ctypes.windll.user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    ctypes.windll.user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    ctypes.windll.user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD]

def setup_gui_window(win_name, width, height):
    global cached_hwnd
    try:
        init_win32_argtypes()
        hwnd = ctypes.windll.user32.FindWindowW(None, win_name)
        if not hwnd:
            return None
        cached_hwnd = hwnd
            
        # 1. Atur Transparansi (60% Opacity)
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        LWA_ALPHA = 0x00000002
        
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED)
        
        # 60% transparansi / opacity (sesuaikan nilai 0.60 ini sesuai keinginan)
        alpha_val = int(255 * 0.60)
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, alpha_val, LWA_ALPHA)
        
        # 2. Hitung Posisi Pojok Kanan Bawah Di Atas Taskbar
        rect = wintypes.RECT()
        SPI_GETWORKAREA = 0x0030
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        
        margin_x = 15
        margin_y = 15
        pos_x = rect.right - width - margin_x
        pos_y = rect.bottom - height - margin_y
        
        # 3. Jadikan Always on Top (Topmost) & Pindahkan Posisi
        HWND_TOPMOST = wintypes.HWND(-1)
        SWP_SHOWWINDOW = 0x0040
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, pos_x, pos_y, width, height, SWP_SHOWWINDOW)
        return hwnd
    except Exception as e:
        print(f"[WARNING] Gagal atur GUI Windows: {e}")
        return None

def display_and_check_exit(frame_to_show):
    global window_setup_done, cached_hwnd
    gui_frame = cv2.resize(frame_to_show, (360, 202))
    cv2.imshow(window_name, gui_frame)
    key = cv2.waitKey(1) & 0xFF
    
    if not window_setup_done:
        cached_hwnd = setup_gui_window(window_name, 360, 202)
        if cached_hwnd:
            window_setup_done = True
    else:
        # Paksakan status Always on Top (Topmost) secara konstan pada setiap frame
        # agar tidak tertimpa aplikasi apa pun saat mengklik atau mengedit file lain.
        try:
            if cached_hwnd:
                HWND_TOPMOST = wintypes.HWND(-1)
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_NOACTIVATE = 0x0010
                ctypes.windll.user32.SetWindowPos(cached_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        except Exception:
            pass
        
    if key == ord('q'):
        return True
    try:
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            return True
    except Exception:
        return True
    return False

print("[SYSTEM] Sistem Kursor Magic Bimanual Aktif! Tekan 'q' atau tombol X pada window untuk keluar.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    # Mirroring & Proses MediaPipe
    frame = cv2.flip(frame, 1)
    h_cam, w_cam, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    left_hand_coords = [0.0] * 63
    right_hand_coords = [0.0] * 63
    left_hand_active = False
    right_hand_active = False
    hand_landmarks_left = None
    hand_landmarks_right = None

    # Ekstrak data koordinat tangan jika terdeteksi
    if results.multi_hand_landmarks and results.multi_handedness:
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Klasifikasi Tangan Kiri/Kanan dengan penyesuaian Mirroring
            mp_label = results.multi_handedness[idx].classification[0].label
            hand_label = 'Right' if mp_label == 'Left' else 'Left'
            
            # Ambil koordinat 63 dimensi
            coords = []
            for lm in hand_landmarks.landmark:
                coords.extend([lm.x, lm.y, lm.z])
                
            if hand_label == 'Left':
                left_hand_coords = coords
                left_hand_active = True
                hand_landmarks_left = hand_landmarks
            else:
                right_hand_coords = coords
                right_hand_active = True
                hand_landmarks_right = hand_landmarks

    # Lakukan prediksi dengan Confidence Thresholding (Minimal 75% Keyakinan)
    gesture = None
    if left_hand_active or right_hand_active:
        X_input = left_hand_coords + right_hand_coords
        X_scaled = scaler.transform([X_input])
        if hasattr(model, 'predict_proba'):
            probs = model.predict_proba(X_scaled)[0]
            max_prob = np.max(probs)
            if max_prob >= 0.75:  # Confidence threshold untuk mencegah false positive
                gesture = int(np.argmax(probs))
        else:
            prediction = model.predict(X_scaled)
            gesture = int(prediction[0])

    # ----------------- LOGIKA 4: LOCK / UNLOCK (PAUSE) -----------------
    # Menggunakan Non-blocking timer (tanpa time.sleep) untuk mencegah UI freeze
    if (left_hand_active or right_hand_active) and gesture == 7:
        if pause_toggle_start is None:
            pause_toggle_start = time.time()
        elif time.time() - pause_toggle_start > 1.0:
            if time.time() - last_pause_toggle_time > 1.5:
                is_paused = not is_paused
                last_pause_toggle_time = time.time()
            pause_toggle_start = None
    else:
        pause_toggle_start = None

    # Jika mode PAUSE aktif, kunci seluruh gerakan dan gambar overlay khusus
    if is_paused:
        # Overlay semi-transparan merah
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w_cam, h_cam), (0, 0, 150), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        
        cv2.putText(frame, "✊ SYSTEM LOCKED / STANDBY ✊", (w_cam // 2 - 270, h_cam // 2 - 20),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 3)
        cv2.putText(frame, "Genggam tangan (fist ✊) selama 1.0 detik untuk UNLOCK", 
                    (w_cam // 2 - 310, h_cam // 2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Reset state lainnya
        if is_dragging:
            pyautogui.mouseUp()
            is_dragging = False
        prev_right_angle = prev_left_angle = prev_scroll_x = prev_scroll_y = None
        pinch_start_time = None
        
        if display_and_check_exit(frame): break
        continue

    # ----------------- LOGIKA 4: KEYBOARD HANTU TOGGLE -----------------
    # Menggunakan Non-blocking timer untuk toggle hologram keyboard
    if left_hand_active and right_hand_active and gesture == 3:
        if keyboard_toggle_start is None:
            keyboard_toggle_start = time.time()
        elif time.time() - keyboard_toggle_start > 2.0:
            if time.time() - last_keyboard_toggle_time > 1.5:
                keyboard_active = not keyboard_active
                last_keyboard_toggle_time = time.time()
            keyboard_toggle_start = None
    else:
        keyboard_toggle_start = None

    # ----------------- JALANKAN LOGIKA SESUAI STATE AKTIF -----------------
    if keyboard_active:
        # Tulis petunjuk di bagian atas
        cv2.rectangle(frame, (0, 0), (w_cam, 70), (30, 20, 20), -1)
        cv2.putText(frame, "⌨️ KEYBOARD HANTU AKTIF (Aksi Mouse Beku)", (20, 45), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, "Tahan Peace ganda 2 detik untuk keluar", (w_cam - 380, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)

        # Gambar Keyboard Virtual (Semi-transparan)
        overlay = frame.copy()
        for k in keyboard_keys:
            cv2.rectangle(overlay, (k['x1'], k['y1']), (k['x2'], k['y2']), (80, 50, 50), -1)
            cv2.rectangle(overlay, (k['x1'], k['y1']), (k['x2'], k['y2']), (150, 150, 150), 1)
            cv2.putText(overlay, k['key'], (k['x1'] + 15, k['y1'] + 45), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        # Deteksi jari hover di tombol keyboard
        active_fingers = []
        if left_hand_active:
            active_fingers.append(hand_landmarks_left.landmark[8])
        if right_hand_active:
            active_fingers.append(hand_landmarks_right.landmark[8])

        current_hovered_keys = set()

        for finger in active_fingers:
            fx = int(finger.x * w_cam)
            fy = int(finger.y * h_cam)
            # Gambar visual penunjuk jari
            cv2.circle(frame, (fx, fy), 12, (255, 100, 0), -1)
            cv2.circle(frame, (fx, fy), 12, (255, 255, 255), 2)

            for k in keyboard_keys:
                if k['x1'] <= fx <= k['x2'] and k['y1'] <= fy <= k['y2']:
                    current_hovered_keys.add(k['key'])
                    
                    # Highlight tombol yang sedang di-hover
                    cv2.rectangle(frame, (k['x1'], k['y1']), (k['x2'], k['y2']), (255, 150, 0), -1)
                    cv2.putText(frame, k['key'], (k['x1'] + 15, k['y1'] + 45), 
                                cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 2)
                    
                    if k['key'] not in hover_start:
                        hover_start[k['key']] = time.time()
                    else:
                        elapsed = time.time() - hover_start[k['key']]
                        # Gambarkan bar progres pengisian
                        progress_w = int((min(elapsed, 1.0) / 1.0) * 80)
                        cv2.rectangle(frame, (k['x1'] + 10, k['y2'] - 10), 
                                      (k['x1'] + 10 + progress_w, k['y2'] - 5), (0, 255, 0), -1)
                        
                        # Jika sudah ditahan selama 1 detik, ketik karakternya
                        if elapsed >= 1.0 and (time.time() - last_typed_time > 0.8):
                            char = k['key']
                            if char == 'Close':
                                keyboard_active = False
                            elif char == 'Back':
                                pyautogui.press('backspace')
                            elif char == 'Space':
                                pyautogui.press('space')
                            elif char == 'Enter':
                                pyautogui.press('enter')
                            else:
                                pyautogui.write(char.lower())
                            
                            last_typed_time = time.time()
                            hover_start[char] = time.time() + 1.0 # Hindari spam beruntun

        # Bersihkan tombol yang sudah tidak di-hover lagi
        for key_name in list(hover_start.keys()):
            if key_name not in current_hovered_keys:
                hover_start.pop(key_name, None)

    else:
        # Reset visual keyboard hover jika dimatikan
        hover_start.clear()

        # ----------------- LOGIKA 4: SCREENSHOT AREA -----------------
        if left_hand_active and right_hand_active and gesture == 4:
            if screenshot_cooldown == 0.0 or (time.time() - screenshot_cooldown > 2.0):
                if screenshot_start is None:
                    screenshot_start = time.time()
                
                # Cari bounding box dari jari telunjuk dan jempol kedua tangan
                L_idx = hand_landmarks_left.landmark[8]
                L_thb = hand_landmarks_left.landmark[4]
                R_idx = hand_landmarks_right.landmark[8]
                R_thb = hand_landmarks_right.landmark[4]
                
                x_min = min(L_idx.x, L_thb.x, R_idx.x, R_thb.x)
                y_min = min(L_idx.y, L_thb.y, R_idx.y, R_thb.y)
                x_max = max(L_idx.x, L_thb.x, R_idx.x, R_thb.x)
                y_max = max(L_idx.y, L_thb.y, R_idx.y, R_thb.y)
                
                # Koordinat kamera untuk overlay visual bingkai
                x1_cam, y1_cam = int(x_min * w_cam), int(y_min * h_cam)
                x2_cam, y2_cam = int(x_max * w_cam), int(y_max * h_cam)
                
                # Menggambar bingkai kamera keren di monitor
                cv2.rectangle(frame, (x1_cam, y1_cam), (x2_cam, y2_cam), (0, 255, 255), 2)
                # Sudut siku-siku bingkai
                size = 20
                cv2.line(frame, (x1_cam, y1_cam), (x1_cam + size, y1_cam), (0, 255, 0), 4)
                cv2.line(frame, (x1_cam, y1_cam), (x1_cam, y1_cam + size), (0, 255, 0), 4)
                cv2.line(frame, (x2_cam, y1_cam), (x2_cam - size, y1_cam), (0, 255, 0), 4)
                cv2.line(frame, (x2_cam, y1_cam), (x2_cam, y1_cam + size), (0, 255, 0), 4)
                cv2.line(frame, (x1_cam, y2_cam), (x1_cam + size, y2_cam), (0, 255, 0), 4)
                cv2.line(frame, (x1_cam, y2_cam), (x1_cam, y2_cam - size), (0, 255, 0), 4)
                cv2.line(frame, (x2_cam, y2_cam), (x2_cam - size, y2_cam), (0, 255, 0), 4)
                cv2.line(frame, (x2_cam, y2_cam), (x2_cam, y2_cam - size), (0, 255, 0), 4)
                
                # Progres bar hitung mundur di layar
                elapsed = time.time() - screenshot_start
                pct = min(elapsed / 1.5, 1.0)
                cv2.rectangle(frame, (x1_cam, y1_cam - 15), (x1_cam + int(pct * (x2_cam - x1_cam)), y1_cam - 5), (0, 255, 0), -1)
                
                if elapsed >= 1.5:
                    scr_w, scr_h = pyautogui.size()
                    # Mapping koordinat ke resolusi layar monitor
                    x1_scr = int(x_min * scr_w)
                    y1_scr = int(y_min * scr_h)
                    x2_scr = int(x_max * scr_w)
                    y2_scr = int(y_max * scr_h)
                    
                    x1_scr = max(0, min(scr_w - 1, x1_scr))
                    y1_scr = max(0, min(scr_h - 1, y1_scr))
                    x2_scr = max(0, min(scr_w - 1, x2_scr))
                    y2_scr = max(0, min(scr_h - 1, y2_scr))
                    
                    w_region = x2_scr - x1_scr
                    h_region = y2_scr - y1_scr
                    
                    if w_region > 20 and h_region > 20:
                        os.makedirs('Data/screenshots', exist_ok=True)
                        filepath = f"Data/screenshots/screenshot_{int(time.time())}.png"
                        pyautogui.screenshot(filepath, region=(x1_scr, y1_scr, w_region, h_region))
                        print(f"[SCREENSHOT] Screenshot Berhasil Disimpan: {filepath}")
                        flash_frames = 4  # Animasi shutter flash kamera
                    
                    screenshot_start = None
                    screenshot_cooldown = time.time()
        else:
            screenshot_start = None

        # ----------------- LOGIKA 1: MULTIMEDIA & ROTASI (LABEL 2) -----------------
        if gesture == 2:
            # Volume control (EKSKLUSIF TANGAN KANAN)
            if right_hand_active:
                w_pt = hand_landmarks_right.landmark[0]
                m_pt = hand_landmarks_right.landmark[9]
                angle = math.atan2(m_pt.y - w_pt.y, m_pt.x - w_pt.x)
                
                if prev_right_angle is not None:
                    delta = angle - prev_right_angle
                    # Handle lompatan sudut atan2 (-pi ke pi)
                    delta = (delta + math.pi) % (2 * math.pi) - math.pi
                    
                    if delta > 0.08:
                        pyautogui.press('volumeup')
                        prev_right_angle = angle
                    elif delta < -0.08:
                        pyautogui.press('volumedown')
                        prev_right_angle = angle
                else:
                    prev_right_angle = angle
                    
            # Brightness control (EKSKLUSIF TANGAN KIRI)
            if left_hand_active:
                w_pt = hand_landmarks_left.landmark[0]
                m_pt = hand_landmarks_left.landmark[9]
                angle = math.atan2(m_pt.y - w_pt.y, m_pt.x - w_pt.x)
                
                if prev_left_angle is not None:
                    delta = angle - prev_left_angle
                    delta = (delta + math.pi) % (2 * math.pi) - math.pi
                    
                    if delta > 0.08:
                        change_brightness(5)
                        prev_left_angle = angle
                    elif delta < -0.08:
                        change_brightness(-5)
                        prev_left_angle = angle
                else:
                    prev_left_angle = angle
        else:
            prev_right_angle = None
            prev_left_angle = None

        # ----------------- LOGIKA 2: NAVIGASI MOUSE & KLIK -----------------
        # Label 0: Gerak Kursor dari prediksi PKL (Tangan Kanan lurus)
        if gesture == 0 and right_hand_active and not is_dragging:
            raw_x = hand_landmarks_right.landmark[8].x
            raw_y = hand_landmarks_right.landmark[8].y
            
            # EMA Filter smoothing
            cursor_x = alpha * raw_x + (1 - alpha) * cursor_x
            cursor_y = alpha * raw_y + (1 - alpha) * cursor_y
            
            scr_w, scr_h = pyautogui.size()
            x_target = max(5, min(scr_w - 5, int(cursor_x * scr_w)))
            y_target = max(5, min(scr_h - 5, int(cursor_y * scr_h)))
            pyautogui.moveTo(x_target, y_target)
            cv2.putText(frame, "🖱️ Move Mode (Label 0)", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)

        # Label 1: Aksi Klik Kiri, Klik Kanan, Double Klik, & Hold-Drag (dari prediksi PKL)
        # ATAU jika sedang tahan-seret (Hold-Drag) agar tidak putus saat fluktuasi frame AI
        elif (gesture == 1 or is_dragging) and right_hand_active:
            t_tip = hand_landmarks_right.landmark[4]
            i_tip = hand_landmarks_right.landmark[8]
            m_tip = hand_landmarks_right.landmark[12]
            
            dist_left = calculate_distance(t_tip, i_tip)
            dist_right = calculate_distance(t_tip, m_tip)
            now = time.time()
            
            # 1. Deteksi Klik Kanan (Cubit Jempol + Jari Tengah Kanan)
            if dist_right < 0.055 and (dist_right < dist_left - 0.005 or dist_left >= 0.055):
                if is_dragging:
                    pyautogui.mouseUp()
                    is_dragging = False
                pinch_start_time = None
                
                if now - last_click_time > 0.35:
                    pyautogui.click(button='right')
                    last_click_time = now
                    last_click_type = 'right'
                cv2.putText(frame, "🔥 RIGHT CLICK! (Label 1)", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 3)
            
            # 2. Deteksi Cubit Kiri (Jempol + Telunjuk Kanan) untuk Klik Kiri / Double Klik / Drag
            elif dist_left < 0.055 and dist_left <= dist_right:
                if pinch_start_time is None:
                    pinch_start_time = now
                elif now - pinch_start_time > 0.28:
                    # Jika cubitan ditahan lebih dari 0.28 detik -> DRAG
                    if not is_dragging:
                        pyautogui.mouseDown()
                        is_dragging = True
                    
                # Pindahkan kursor saat cubitan ditahan / drag
                raw_x = i_tip.x
                raw_y = i_tip.y
                cursor_x = alpha * raw_x + (1 - alpha) * cursor_x
                cursor_y = alpha * raw_y + (1 - alpha) * cursor_y
                scr_w, scr_h = pyautogui.size()
                x_target = max(5, min(scr_w - 5, int(cursor_x * scr_w)))
                y_target = max(5, min(scr_h - 5, int(cursor_y * scr_h)))
                pyautogui.moveTo(x_target, y_target)
                if is_dragging:
                    cv2.putText(frame, "✊ DRAG MODE (HOLD)", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "🤏 PINCH (CLICKING...)", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 0), 2)
            
            # 3. Cubitan Dilepas saat dalam mode Label 1
            else:
                if is_dragging:
                    pyautogui.mouseUp()
                    is_dragging = False
                elif pinch_start_time is not None:
                    # Dilepas dengan cepat (< 0.28 detik) -> KLIK KIRI / DOUBLE KLIK
                    if now - pinch_start_time < 0.28:
                        if last_click_type == 'left' and (now - last_click_time < 0.65):
                            pyautogui.doubleClick()
                            last_click_time = now
                            last_click_type = 'double'
                            cv2.putText(frame, "🔥🔥 DOUBLE CLICK!", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 3)
                        else:
                            pyautogui.click(button='left')
                            last_click_time = now
                            last_click_type = 'left'
                            cv2.putText(frame, "🔥 LEFT CLICK!", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 3)
                pinch_start_time = None
                
                # Pindahkan kursor jika dilepas
                raw_x = hand_landmarks_right.landmark[8].x
                raw_y = hand_landmarks_right.landmark[8].y
                cursor_x = alpha * raw_x + (1 - alpha) * cursor_x
                cursor_y = alpha * raw_y + (1 - alpha) * cursor_y
                scr_w, scr_h = pyautogui.size()
                x_target = max(5, min(scr_w - 5, int(cursor_x * scr_w)))
                y_target = max(5, min(scr_h - 5, int(cursor_y * scr_h)))
                pyautogui.moveTo(x_target, y_target)
                cv2.putText(frame, "🤏 Click Mode Ready (Label 1)", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
        else:
            if is_dragging:
                pyautogui.mouseUp()
                is_dragging = False
            pinch_start_time = None

        # ----------------- LOGIKA 3: SCROLL & SWIPE TAB -----------------
        # Label 5: Scroll (Ninja - Jari telunjuk & tengah lurus sejajar)
        if gesture == 5:
            # Cari tangan mana yang aktif untuk scroll (Kanan prioritas)
            active_h = hand_landmarks_right if right_hand_active else hand_landmarks_left
            if active_h:
                curr_x = active_h.landmark[9].x
                curr_y = active_h.landmark[9].y
                
                if prev_scroll_y is not None and prev_scroll_x is not None:
                    dy = curr_y - prev_scroll_y
                    dx = curr_x - prev_scroll_x
                    
                    if abs(dy) > 0.015:
                        scroll_amount = int(dy * 2500)
                        pyautogui.scroll(-scroll_amount)
                        prev_scroll_y = curr_y
                    if abs(dx) > 0.015:
                        hscroll_amount = int(dx * 2500)
                        pyautogui.hscroll(hscroll_amount)
                        prev_scroll_x = curr_x
                else:
                    prev_scroll_y = curr_y
                    prev_scroll_x = curr_x
                cv2.putText(frame, "🧭 Ninja Scroll", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
        else:
            prev_scroll_y = None

        # Label 6: Swipe Kanan Kiri / Horizontal Scroll (Tangan Terbuka Kertas)
        # Berfungsi seperti scroll horizontal ke kanan dan ke kiri (tanpa memindahkan kursor mouse)
        if gesture == 6:
            active_h = hand_landmarks_left if left_hand_active else hand_landmarks_right
            if active_h:
                curr_x = active_h.landmark[9].x  # MCP telapak tangan (lebih stabil dari pergelangan)
                
                if prev_scroll_x is not None:
                    dx = curr_x - prev_scroll_x
                    if abs(dx) > 0.012:
                        hscroll_amount = int(dx * 3000)
                        pyautogui.hscroll(hscroll_amount)
                        prev_scroll_x = curr_x
                else:
                    prev_scroll_x = curr_x
                cv2.putText(frame, "↔️ Horizontal Swipe / Scroll (Label 6)", (50, 50), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
        else:
            if gesture != 5:
                prev_scroll_x = None

    # Visualisasi Tambahan di Pojok Layar
    cv2.putText(frame, f"AI Label: {gesture if gesture is not None else '-'}", (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    # Animasi Shutter Flash Kamera saat screenshot berhasil
    if flash_frames > 0:
        cv2.rectangle(frame, (0, 0), (w_cam, h_cam), (255, 255, 255), -1)
        flash_frames -= 1

    if display_and_check_exit(frame):
        break

cap.release()
cv2.destroyAllWindows()
print("Sistem Kursor Magic Selesai.")
