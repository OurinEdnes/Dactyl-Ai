import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

csv_path = 'Data/dataset_bimanual.csv'
model_dir = 'models'
model_path = os.path.join(model_dir, 'svm_gesture_model.pkl')
eval_log_path = os.path.join(model_dir, 'training_evaluation.txt')

print("Memulai proses pelatihan model AI Dactyl-AI (Enhanced Pipeline)...")

if not os.path.exists(csv_path):
    print(f"Error: File {csv_path} tidak ditemukan.")
    exit()

kolom_koordinat = [f'k_{i}' for i in range(126)]
header = ['label'] + kolom_koordinat
df = pd.read_csv(csv_path, header=None, names=header)

X = df.drop('label', axis=1) 
y = df['label']

# Split pertama: 80% Train, 20% Temp
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
# Split kedua: 50% dari Temp untuk Val (10% total), 50% untuk Test (10% total)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

def get_distribution_str(y_data, name):
    dist = y_data.value_counts(normalize=True).sort_index() * 100
    counts = y_data.value_counts().sort_index()
    res = f"\nDistribusi {name} (Total: {len(y_data)}):\n"
    for label, count in counts.items():
        res += f"  Label {label}: {count} sampel ({dist[label]:.1f}%)\n"
    return res

print(f"Total data: {len(df)} baris")
print(get_distribution_str(y_train, "Train Set"))
print(get_distribution_str(y_val, "Validation Set"))
print(get_distribution_str(y_test, "Test Set"))

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

# Penanganan Imbalanced Dataset (4.41 : 1) menggunakan class_weight='balanced'
model = SVC(kernel='rbf', probability=True, C=10, gamma='scale', class_weight='balanced', random_state=42)

# 10-Fold Stratified Cross-Validation pada Train Set untuk Stabilitas Ilmiah
print("\n--- MENJALANKAN 10-FOLD STRATIFIED CROSS-VALIDATION ---")
skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=skf, scoring='accuracy')
cv_mean = cv_scores.mean() * 100
cv_std = cv_scores.std() * 100
print(f"10-Fold CV Accuracy: {cv_mean:.2f}% (+/- {cv_std:.2f}%)")

model.fit(X_train_scaled, y_train)

print("\n--- EVALUASI VALIDASI (Fase Tuning) ---")
val_pred = model.predict(X_val_scaled)
val_acc = accuracy_score(y_val, val_pred) * 100
print(f"Akurasi Validasi: {val_acc:.2f}%")
val_report = classification_report(y_val, val_pred)
print(val_report)

print("\n--- EVALUASI FINAL (Fase Test) ---")
test_pred = model.predict(X_test_scaled)
test_acc = accuracy_score(y_test, test_pred) * 100
print(f"Akurasi Final (Test): {test_acc:.2f}%")
test_report = classification_report(y_test, test_pred)
print(test_report)

test_cm = confusion_matrix(y_test, test_pred)

if not os.path.exists(model_dir):
    os.makedirs(model_dir, exist_ok=True)

with open(model_path, 'wb') as f:
    pickle.dump({'model': model, 'scaler': scaler}, f)

# Simpan log evaluasi untuk bukti empiris jurnal ilmiah
with open(eval_log_path, 'w') as log_f:
    log_f.write("=== LAPORAN EVALUASI PELATIHAN MODEL DACTYL-AI V2.5 ===\n")
    log_f.write(f"Total Dataset: {len(df)} baris (126 koordinat fitur)\n")
    log_f.write(f"Konfigurasi SVM: kernel='rbf', C=10, gamma='scale', class_weight='balanced'\n\n")
    log_f.write(f"10-Fold Stratified Cross-Validation Accuracy: {cv_mean:.2f}% (+/- {cv_std:.2f}%)\n\n")
    log_f.write(f"Validation Set Accuracy: {val_acc:.2f}%\n")
    log_f.write("Validation Classification Report:\n" + val_report + "\n")
    log_f.write(f"Test Set Accuracy: {test_acc:.2f}%\n")
    log_f.write("Test Classification Report:\n" + test_report + "\n")
    log_f.write("Test Set Confusion Matrix:\n" + str(test_cm) + "\n")

print(f"Berhasil: Otak AI dan Formula Scaler telah disimpan di: {model_path}")
print(f"Log Evaluasi Ilmiah tersimpan di: {eval_log_path}")