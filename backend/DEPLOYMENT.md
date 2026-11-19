# AirSense backend deployment

Dokumentasi ini mencakup target utama Vercel dan opsi Docker lokal.

## Backend Vercel

Atur Root Directory Vercel proyek backend ke `backend`.

- Framework preset: Django
- Entry point WSGI: `config/wsgi:application`
- Python: 3.12
- Build script: `python build_vercel.py`
- Konfigurasi function: `vercel.json`
- Dokumentasi khusus: `VERCEL.md`

Jangan mengunduh atau menyimpan secret melalui build arguments.
Gunakan environment variables Vercel untuk secret dan origin production.

## Frontend Vercel

Atur Root Directory proyek frontend ke `frontend`.

- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_BASE_URL=https://DOMAIN-BACKEND.vercel.app/api`

## Local Docker build

```bash
cd backend
docker build -t airsense-backend .
```

The Docker build downloads `airsense_models.joblib` from GitHub Release `v1.0.0`,
stores it at `ml/artifacts/airsense_models.joblib`, validates the artifact structure,
and keeps `metrics.json` from the repository.

## Run locally

Create `backend/.env` from `.env.example`, then run:

```bash
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  -e PORT=8000 \
  airsense-backend
```

Do not pass the Groq key or Django secret through Docker build arguments.

## Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `SECRET_KEY` | Production | Django cryptographic secret |
| `DEBUG` | Yes | Set `false` in production |
| `ALLOWED_HOSTS` | Yes | Comma-separated public API hostnames |
| `CORS_ALLOWED_ORIGINS` | Yes | Comma-separated frontend origins |
| `CSRF_TRUSTED_ORIGINS` | If needed | Comma-separated trusted HTTPS origins |
| `GROQ_API_KEY` | Optional | Enables AI explanation endpoint |
| `GROQ_MODEL` | Optional | Defaults to `openai/gpt-oss-20b` |
| `PORT` | Docker | Listening port; Gunicorn falls back to `8000` |
| `SECURE_SSL_REDIRECT` | Optional | Defaults to `true` when `DEBUG=false` |
| `SESSION_COOKIE_SECURE` | Optional | Defaults to `true` when `DEBUG=false` |
| `CSRF_COOKIE_SECURE` | Optional | Defaults to `true` when `DEBUG=false` |
| `SECURE_HSTS_SECONDS` | Optional | HSTS duration; defaults to `0` |

Vercel and compatible reverse proxies terminate TLS before the Django app.
The Django settings trust
`X-Forwarded-Proto: https` for secure URL and cookie behavior.

## Verify deployment

```bash
curl https://api.example.com/api/health/
curl https://api.example.com/api/metrics/
```

The health response has `model_ready: true` only after the artifact loads
successfully. Prediction and AI request examples are documented by the existing
API routes; do not change those contracts.
