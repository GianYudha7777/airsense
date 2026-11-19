# AirSense — Air Quality Prediction System

Prototipe pembelajaran Machine Learning untuk memperkirakan konsentrasi polutan dari respons 5 sensor kimia dan 3 variabel lingkungan.

## Apa yang dilakukan aplikasi?

1. Pengguna mengisi 8 input: PT08.S1 sampai PT08.S5, suhu, kelembapan relatif, dan kelembapan absolut.
2. Django REST API memuat model Random Forest yang sudah dilatih.
3. Model memprediksi konsentrasi CO, benzena (C6H6), NOx, dan NO2.
4. Aplikasi menampilkan nilai prediksi dan kategori Baik/Sedang/Buruk.
5. Vue menampilkan ringkasan serta grafik jumlah kategori pada empat polutan.

**Penting:** kategori Baik/Sedang/Buruk pada prototipe ini adalah kategori relatif berdasarkan kuantil (sepertiga dan dua pertiga) dari data training. Kategori ini BUKAN ISPU resmi, bukan diagnosis risiko kesehatan, dan bukan pengukuran langsung. Dataset UCI berasal dari area perkotaan di Italia pada 2004–2005, sehingga hasilnya tidak boleh dianggap sebagai gambaran kualitas udara saat ini di Indonesia.

## Sumber dataset

UCI Machine Learning Repository — Air Quality (ID 360):
https://archive.ics.uci.edu/dataset/360/air%2Bquality

DOI: https://doi.org/10.24432/C59K5F

Dataset memiliki 9.358 observasi rata-rata per jam. File `backend/ml/data/raw/AirQualityUCI.csv` disimpan lokal; training tidak mengunduh dataset. Nilai hilang pada data sumber ditandai dengan `-200`; script training mengubah nilai itu menjadi missing value dan membersihkannya.

UCI menyatakan dataset ini hanya untuk keperluan riset dan mengecualikan penggunaan komersial. Periksa ketentuan pada halaman sumber sebelum penggunaan di luar konteks pembelajaran/riset.

## Struktur folder

```text
airsense-project/
├── backend/
│   ├── config/                 # Konfigurasi Django
│   ├── predictor/              # REST API
│   ├── ml/
│   │   ├── train_model.py      # Bersihkan data lokal, training, evaluasi
│   │   └── artifacts/          # File model .joblib hasil training
│   ├── requirements.txt
│   └── manage.py
└── frontend/
    ├── src/
    │   ├── services/api.js
    │   ├── App.vue
    │   └── style.css
    └── package.json
```

## Persiapan di Ubuntu

### 1. Instal kebutuhan sistem

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential curl git
```

Install Node.js LTS (disarankan Node.js 22 LTS atau versi LTS lebih baru yang kompatibel dengan Vite):

```bash
# Pasang NVM (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install --lts
nvm use --lts
node --version
npm --version
```

Jika NVM sudah terpasang, tidak perlu memasangnya lagi. Cukup jalankan `nvm install --lts` dan `nvm use --lts`.

### 2. Siapkan environment dan backend Django

Buat environment utama di root project:

```bash
cd airsense-project
python3 -m venv .venv-1
source .venv-1/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 3. Training model (wajib dilakukan sekali sebelum prediksi)

Pastikan file CSV lokal tersedia di `backend/ml/data/raw/AirQualityUCI.csv`:

```bash
cd backend
python ml/train_model.py
```

Script akan:
- membaca dataset UCI ID 360 dari file CSV lokal;
- memilih 8 fitur input dan 4 target;
- mengubah `-200` menjadi nilai hilang;
- mengisi nilai sensor yang hilang menggunakan median dari data training;
- melatih satu Random Forest Regressor untuk setiap target;
- mengevaluasi model pada bagian akhir urutan data (pemisahan kronologis 80:20);
- menyimpan model di `backend/ml/artifacts/airsense_models.joblib` dan metrik di `backend/ml/artifacts/metrics.json`.

Jika training selesai, lanjutkan:

```bash
python manage.py migrate
python manage.py runserver
```

Backend berjalan di `http://127.0.0.1:8000`.

### 4. Siapkan frontend Vue

Buka terminal kedua:

```bash
cd airsense-project/frontend
npm ci
npm run dev
```

Buka URL yang ditampilkan Vite, biasanya `http://localhost:5173`.

## Urutan menjalankan setelah instalasi pertama

Terminal 1:

```bash
cd airsense-project
source .venv-1/bin/activate
cd backend
python manage.py runserver
```

Terminal 2:

```bash
cd airsense-project/frontend
npm run dev
```

`npm ci` hanya perlu dijalankan saat pertama kali menyiapkan dependency frontend atau setelah `node_modules` dihapus.

Training tidak perlu diulang setiap kali menjalankan aplikasi. Ulangi `python ml/train_model.py` hanya ketika ingin melatih ulang model.

## Endpoint API

- `GET /api/health/` — status backend dan ketersediaan model.
- `GET /api/metrics/` — metrik evaluasi training.
- `POST /api/predict/` — melakukan prediksi.
- `POST /api/ai/explain/` — meminta AI Insight untuk grafik; memerlukan `GROQ_API_KEY` di environment backend.

Contoh body JSON untuk `/api/predict/`:

```json
{
  "sensor_s1": 1360,
  "sensor_s2": 1040,
  "sensor_s3": 950,
  "sensor_s4": 1600,
  "sensor_s5": 1300,
  "temperature": 13.6,
  "relative_humidity": 48.9,
  "absolute_humidity": 0.7578
}
```

Nilai di atas hanya contoh format input, bukan rekomendasi nilai normal atau nilai sensor yang harus digunakan.

## Catatan metodologi

- Model melakukan **regresi** untuk menghasilkan nilai numerik konsentrasi polutan.
- Label Baik/Sedang/Buruk dibuat sesudah regresi dengan membandingkan nilai prediksi terhadap kuantil setiap target pada data training. Ini hanya kategori relatif untuk demonstrasi pembelajaran.
- Satuan antarpolutan berbeda. Jangan membandingkan angka CO, benzena, NOx, dan NO2 secara langsung.
- Data bersifat historis dan menunjukkan drift sensor serta missing value. Nilai prediksi dapat memiliki error dan tidak menggantikan alat ukur resmi.
- UCI mencatat pembatasan/ketentuan penggunaan dataset; periksa kembali halaman sumber dan ketentuan lisensi sebelum penggunaan di luar pembelajaran.

## Troubleshooting

**`Model belum tersedia`**

Jalankan training dari folder `backend`:

```bash
python ml/train_model.py
```

**Dataset training tidak ditemukan**

Pastikan `AirQualityUCI.csv` tersedia di `backend/ml/data/raw/`.

**Frontend tidak dapat menghubungi backend**

Pastikan Django berjalan pada port 8000 dan Vite pada port 5173. Konfigurasi proxy berada di `frontend/vite.config.js`.
