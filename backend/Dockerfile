FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir gunicorn==23.0.0

COPY . .

RUN set -eu; \
    trap 'rm -f /app/ml/artifacts/airsense_models.joblib.download' EXIT; \
    mkdir -p /app/ml/artifacts; \
    curl --fail --location --retry 3 --retry-delay 2 \
        --output /app/ml/artifacts/airsense_models.joblib.download \
        https://github.com/GianYudha7777/airsense/releases/download/v1.0.0/airsense_models.joblib; \
    test -s /app/ml/artifacts/airsense_models.joblib.download; \
    actual_sha256="$(sha256sum /app/ml/artifacts/airsense_models.joblib.download | awk '{print $1}')"; \
    if [ "$actual_sha256" != "5d611619c3430096320866d71d74dbeb93ffcd7fe202fb8f7eb842dd0448d355" ]; then \
        echo "Model SHA-256 mismatch: expected 5d611619c3430096320866d71d74dbeb93ffcd7fe202fb8f7eb842dd0448d355, got $actual_sha256" >&2; \
        exit 1; \
    fi; \
    mv /app/ml/artifacts/airsense_models.joblib.download /app/ml/artifacts/airsense_models.joblib; \
    python -c "import joblib; b=joblib.load('/app/ml/artifacts/airsense_models.joblib'); required={'models','thresholds','feature_columns','model_feature_columns','target_columns','artifact_version'}; missing=required.difference(b); assert not missing, f'missing: {sorted(missing)}'; assert b['artifact_version'] == 2, 'unsupported artifact version'"; \
    test -s /app/ml/artifacts/metrics.json

EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2 --timeout 120 --graceful-timeout 30"]
