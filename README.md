# Dactyl-AI: Touchless Cursor & Hologram Keyboard

> **Optimasi Kontrol Cursor dan Input Keyboard Virtual Berbasis Hand-Landmark Detection Menggunakan Arsitektur MediaPipe Secara Real Time**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Hands-green)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-red)
![Machine Learning](https://img.shields.io/badge/ML-KNN%20%2F%20SVM-orange)

## Deskripsi Sistem
**Dactyl-AI** adalah solusi *Human-Computer Interaction* (HCI) mutakhir yang memungkinkan pengguna mengontrol kursor dan mengetik tanpa menyentuh perangkat keras fisik (mouse/keyboard). Sistem ini menggunakan kamera web dan **MediaPipe Hands** untuk mengekstraksi 21 titik koordinat (*hand-landmarks*) secara *real-time*.

Sistem beroperasi dalam dua mode dinamis:
1. **Mode Navigasi:** Menggerakkan kursor menggunakan tangan dominan dan melakukan aksi klik melalui gestur *pinch* (mencubit).
2. **Mode Hologram Keyboard:** Mengaktifkan (*summoning*) keyboard virtual transparan di layar menggunakan gestur V-Sign ganda. Pengguna dapat mengetik di udara dengan melakukan *pinch* pada area tombol *bounding-box*.

Klasifikasi gestur didukung oleh model Machine Learning ringan (KNN/SVM) yang dilatih menggunakan dataset 1000+ baris koordinat spasial, memastikan performa stabil di angka **24-30 FPS**.

---

## Fitur Utama
- **Real-Time Spatio-Temporal Tracking:** Pelacakan pergerakan tangan tanpa *lag* menggunakan MediaPipe.
- **Dual-Wielding Interface:** Pembagian tugas efisien antara tangan penunjuk navigasi dan tangan pengetik virtual untuk mencegah *oklusi* (jari saling menutupi).
- **Hologram Keyboard Summoning:** Sistem pemanggilan keyboard berbasis *Rule-Based Logic* (Dual V-Sign).
- **Heuristic Jitter Filtering:** Algoritma peredam getaran alami tangan agar kursor tetap stabil (*smooth*).
- **Lightweight AI Engine:** Pengklasifikasian gestur menggunakan koordinat vektor (X, Y, Z), bukan citra gambar, sehingga tidak membebani GPU.

---

## Arsitektur & Metodologi
- **Computer Vision:** OpenCV (Video Capture & Rendering UI)
- **Feature Extraction:** MediaPipe Hands (21 Landmark Nodes)
- **Machine Learning / Logic:** Scikit-Learn (SVM/KNN untuk klasifikasi gestur) & Euclidean Distance (Kalkulasi jarak antar jari).
- **Data Representation:** Frame-Based, Rule-Based (IF-THEN), dan Temporal-State (Idle, Active, Hold).

---

## Cara Instalasi & Penggunaan

### 1. Prasyarat
Pastikan Python sudah terpasang di sistem Anda (versi 3.8 ke atas).

### 2. Clone Repository
```bash
git clone [https://github.com/USERNAME_KALIAN/Dactyl-AI.git](https://github.com/USERNAME_KALIAN/Dactyl-AI.git)
cd Dactyl-AI
