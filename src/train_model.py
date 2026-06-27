import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

# =======================================================
# 🦈 SCRIPT PELATIHAN AI (MODEL TRAINING) OURIN 🦈
# =======================================================

csv_path = 'Data/dataset_bimanual.csv'
model_dir = 'models'
model_path = os.path.join(model_dir, 'svm_gesture_model.pkl')

print("🦈 Memulai proses penyekolahan AI Aikoo...")

if not os.path.exists(csv_path):
    print(f"❌ Error: File {csv_path} belum ada!")
    exit()

print("📊 Sedang membaca Buku Pelajaran (Dataset)...")

# --- AIKOO MAGIC: Otomatis nambahin header kalau filenya polos ---
# Kita buat list nama kolom: 'label' diikuti 126 kolom koordinat
kolom_koordinat = [f'k_{i}' for i in range(126)]
header = ['label'] + kolom_koordinat

df = pd.read_csv(csv_path, header=None, names=header)

# Cek hasil load
print(f"✅ Data berhasil dimuat! Total: {len(df)} baris.")

# Memisahkan Kolom Label dengan Fitur
X = df.drop('label', axis=1) 
y = df['label']

# Bagi data: 80% Train, 20% Test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Preprocessing
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Latih Model
print("🧠 Sedang melatih Model AI (Support Vector Machine)...")
model = SVC(kernel='rbf', probability=True, C=10, gamma='scale')
model.fit(X_train_scaled, y_train)

# Testing
print("📝 AI sedang mengerjakan Ujian (Testing)...")
y_pred = model.predict(X_test_scaled)

akurasi = accuracy_score(y_test, y_pred)
print("=========================================")
print(f"🎯 AKURASI KECERDASAN AI: {akurasi * 100:.2f}%")
print("=========================================")

print("\nDetail Nilai Rapor AI:")
print(classification_report(y_test, y_pred))

# Simpan
if not os.path.exists(model_dir):
    os.makedirs(model_dir, exist_ok=True)

with open(model_path, 'wb') as f:
    pickle.dump({'model': model, 'scaler': scaler}, f)

print(f"💾 BERHASIL! Otak AI telah disimpan di: {model_path}")