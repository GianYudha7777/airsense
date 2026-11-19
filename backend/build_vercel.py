from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path

import joblib


MODEL_URL = (
    "https://github.com/GianYudha7777/airsense/releases/download/"
    "v1.0.0/airsense_models.joblib"
)
EXPECTED_SHA256 = "5d611619c3430096320866d71d74dbeb93ffcd7fe202fb8f7eb842dd0448d355"
REQUIRED_KEYS = {
    "models",
    "thresholds",
    "feature_columns",
    "model_feature_columns",
    "target_columns",
    "artifact_version",
}

BACKEND_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BACKEND_DIR / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "airsense_models.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(destination: Path) -> None:
    request = urllib.request.Request(
        MODEL_URL,
        headers={"User-Agent": "AirSense-Vercel-Builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Model download failed with HTTP status {response.status}"
            )
        with destination.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)


def validate_model(path: Path) -> dict:
    bundle = joblib.load(path)
    if not isinstance(bundle, dict):
        raise RuntimeError("Model artifact must contain a dictionary.")

    missing = REQUIRED_KEYS.difference(bundle.keys())
    if missing:
        raise RuntimeError(
            f"Model artifact is missing keys: {sorted(missing)}"
        )
    if bundle["artifact_version"] != 2:
        raise RuntimeError(
            f"Unsupported artifact_version: {bundle['artifact_version']}"
        )
    return bundle


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    if not METRICS_PATH.is_file() or METRICS_PATH.stat().st_size == 0:
        raise RuntimeError(f"Required metrics file is missing: {METRICS_PATH}")

    with METRICS_PATH.open("r", encoding="utf-8") as file:
        json.load(file)

    if MODEL_PATH.is_file() and MODEL_PATH.stat().st_size > 0:
        try:
            existing_sha256 = sha256_file(MODEL_PATH)
            if existing_sha256 == EXPECTED_SHA256:
                validate_model(MODEL_PATH)
                print(
                    f"Valid model artifact already available: {MODEL_PATH} "
                    f"({MODEL_PATH.stat().st_size} bytes)"
                )
                return
            print(
                "Existing model artifact checksum mismatch; downloading replacement."
            )
        except Exception as exc:
            print(
                f"Existing model artifact is invalid; downloading replacement: {exc}"
            )

    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".airsense_models.",
            suffix=".joblib.download",
            dir=ARTIFACT_DIR,
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)

        download_model(temporary_path)
        if temporary_path.stat().st_size == 0:
            raise RuntimeError("Downloaded model file is empty.")

        actual_sha256 = sha256_file(temporary_path)
        if actual_sha256 != EXPECTED_SHA256:
            raise RuntimeError(
                "Model SHA-256 mismatch: "
                f"expected {EXPECTED_SHA256}, got {actual_sha256}"
            )

        validate_model(temporary_path)
        os.replace(temporary_path, MODEL_PATH)
        temporary_path = None

        print(
            f"Model artifact ready: {MODEL_PATH} "
            f"({MODEL_PATH.stat().st_size} bytes, sha256={EXPECTED_SHA256})"
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
