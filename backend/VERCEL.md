# Deployment Django AirSense ke Vercel

## Konfigurasi proyek

Atur Root Directory proyek Vercel ke `backend`. Vercel akan menemukan
`manage.py`, membaca `DJANGO_SETTINGS_MODULE`, dan menggunakan
`config/wsgi.application` sebagai WSGI function.

Alternatifnya, `backend/pyproject.toml` menunjuk ke entrypoint yang sama dan
menjalankan `build_vercel.py` melalui `[tool.vercel.scripts]`.

Python 3.12 dipilih melalui `backend/.python-version`.

## Build model

Pada build, `build_vercel.py`:

1. Mengunduh asset GitHub Release ke file temporary.
2. Memastikan status download berhasil dan file tidak kosong.
3. Memvalidasi SHA-256:
   `5d611619c3430096320866d71d74dbeb93ffcd7fe202fb8f7eb842dd0448d355`.
4. Memuat artifact dengan `joblib` dan memvalidasi semua key wajib serta
   `artifact_version == 2`.
5. Memindahkan artifact secara atomik ke `ml/artifacts/airsense_models.joblib`.
6. Memvalidasi dan memuat `ml/artifacts/metrics.json`.

Checksum yang salah atau artifact/metrics yang tidak valid menghentikan build.
Model tidak perlu dimasukkan ke Git.

## Environment variables

Tambahkan variabel berikut pada environment Vercel:

| Variabel | Kebutuhan |
|---|---|
| `SECRET_KEY` | Wajib untuk production |
| `DEBUG` | `false` untuk production |
| `ALLOWED_HOSTS` | Domain API, dipisah koma |
| `CORS_ALLOWED_ORIGINS` | Domain frontend, dipisah koma |
| `CSRF_TRUSTED_ORIGINS` | HTTPS origin yang dipercaya, jika diperlukan |
| `GROQ_API_KEY` | Opsional |
| `GROQ_MODEL` | Opsional, default `openai/gpt-oss-20b` |

Jangan menyimpan secret pada `vercel.json`, `pyproject.toml`, atau source code.
Vercel menyelesaikan TLS di reverse proxy dan aplikasi mempercayai header
`X-Forwarded-Proto: https`.

## Deployment

```bash
cd backend
npx vercel
```

Gunakan build dari GitHub dengan Root Directory `backend`, atau jalankan
`npx vercel --prod` setelah autentikasi Vercel.

## Verifikasi

```bash
curl https://<domain-vercel>/api/health/
curl https://<domain-vercel>/api/metrics/
```

Health endpoint melaporkan `model_ready: true` jika artifact berhasil dimuat.
Endpoint prediksi dan AI preserve contract URL `/api/predict/` dan
`/api/ai/explain/`.
