"""Train, evaluate, and save the AirSense pollutant regression models.

Run from the backend directory:
    python ml/train_model.py

The dataset is read locally from:
    ml/data/raw/AirQualityUCI.csv

The script first evaluates each target with a chronological 80:20 holdout.
After evaluation, it refits the deployment pipeline on all valid target rows
and saves the final pipelines plus their target-specific feature columns.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BASE_DIR / "ml" / "data" / "raw" / "AirQualityUCI.csv"
ARTIFACT_DIR = BASE_DIR / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "airsense_models.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"

# The form continues to accept all eight variables. Each model selects only
# the features established by the experiments for its own target.
INPUT_FEATURE_COLUMNS = [
    "PT08.S1(CO)",
    "PT08.S2(NMHC)",
    "PT08.S3(NOx)",
    "PT08.S4(NO2)",
    "PT08.S5(O3)",
    "T",
    "RH",
    "AH",
]

TARGET_COLUMNS = ["CO(GT)", "C6H6(GT)", "NOx(GT)", "NO2(GT)"]

FEATURES_BY_TARGET: dict[str, list[str]] = {
    "CO(GT)": INPUT_FEATURE_COLUMNS.copy(),
    "C6H6(GT)": ["PT08.S2(NMHC)"],
    "NOx(GT)": INPUT_FEATURE_COLUMNS.copy(),
    "NO2(GT)": INPUT_FEATURE_COLUMNS.copy(),
}

REQUIRED_COLUMNS = list(
    dict.fromkeys(
        INPUT_FEATURE_COLUMNS
        + TARGET_COLUMNS
    )
)

RANDOM_FOREST_CONFIG = {
    "n_estimators": 220,
    "max_depth": 18,
    "min_samples_leaf": 2,
    "random_state": 42,
    "n_jobs": -1,
}
TEST_FRACTION = 0.20
MIN_VALID_TARGET_ROWS = 100


def build_pipeline() -> Pipeline:
    """Create the preprocessing + regression pipeline."""
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(**RANDOM_FOREST_CONFIG)),
        ]
    )


def load_dataset() -> pd.DataFrame:
    """Read the original UCI CSV format from the local project directory."""
    print(f"[1/6] Membaca dataset lokal: {DATASET_PATH}")

    if not DATASET_PATH.is_file():
        raise FileNotFoundError(
            "Dataset tidak ditemukan.\n"
            f"Lokasi yang diharapkan: {DATASET_PATH}\n"
            "Pastikan AirQualityUCI.csv berada di backend/ml/data/raw/."
        )

    try:
        header = pd.read_csv(
            DATASET_PATH,
            sep=";",
            encoding="latin1",
            nrows=0,
        )
    except Exception as exc:
        raise RuntimeError(f"CSV tidak dapat dibaca: {exc}") from exc

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in header.columns]
    if missing_columns:
        available = ", ".join(map(str, header.columns.tolist()))
        raise KeyError(
            "Kolom dataset tidak sesuai. Kolom yang tidak ditemukan: "
            + ", ".join(missing_columns)
            + ". Kolom yang tersedia: "
            + available
        )

    data = pd.read_csv(
        DATASET_PATH,
        sep=";",
        decimal=",",
        encoding="latin1",
        usecols=REQUIRED_COLUMNS,
        low_memory=False,
    )

    # Enforce a stable column order, convert numeric columns, and remove only
    # rows where every selected feature and target is empty.
    data = data[REQUIRED_COLUMNS].copy()
    data = data.dropna(how="all").reset_index(drop=True)

    for column in REQUIRED_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    # In this UCI dataset, -200 is the documented missing-value marker.
    data = data.replace(-200, np.nan)

    print(f"Dataset berhasil dibaca: {len(data):,} baris")
    print(f"Jumlah input form: {len(INPUT_FEATURE_COLUMNS)}")
    print(f"Jumlah target: {len(TARGET_COLUMNS)}")
    return data


def evaluate_target(
    data: pd.DataFrame,
    target_name: str,
    feature_columns: list[str],
) -> tuple[Pipeline, dict[str, Any], pd.Series]:
    """Evaluate with chronological holdout; return holdout pipeline and stats."""
    y_all = data[target_name]
    valid_target = y_all.notna()

    X = data.loc[valid_target, feature_columns].copy()
    y = y_all.loc[valid_target].copy()

    if len(y) < MIN_VALID_TARGET_ROWS:
        raise RuntimeError(
            f"Target {target_name} hanya memiliki {len(y)} baris valid; "
            f"minimum yang dibutuhkan {MIN_VALID_TARGET_ROWS}."
        )

    split_index = int(len(y) * (1.0 - TEST_FRACTION))
    if split_index <= 0 or split_index >= len(y):
        raise RuntimeError(f"Pembagian train/test tidak valid untuk {target_name}.")

    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    holdout_pipeline = build_pipeline()
    holdout_pipeline.fit(X_train, y_train)
    predictions = holdout_pipeline.predict(X_test)

    result = {
        "mae": float(mean_absolute_error(y_test, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "r2": float(r2_score(y_test, predictions)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "valid_target_rows": int(len(y)),
        "feature_columns": feature_columns,
        "evaluation_method": "chronological_holdout_80_20",
    }
    return holdout_pipeline, result, y


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_dataset()

    print("[2/6] Memeriksa konfigurasi fitur per target...")
    for target_name, feature_columns in FEATURES_BY_TARGET.items():
        if target_name not in TARGET_COLUMNS:
            raise ValueError(f"Target tidak dikenal dalam konfigurasi: {target_name}")
        unknown_features = [
            feature for feature in feature_columns
            if feature not in INPUT_FEATURE_COLUMNS
        ]
        if not feature_columns or unknown_features:
            raise ValueError(
                f"Konfigurasi fitur tidak valid untuk {target_name}: {unknown_features}"
            )
        print(f"  - {target_name}: {len(feature_columns)} fitur")

    print("[3/6] Evaluasi model menggunakan holdout kronologis 80:20...")
    evaluation_metrics: dict[str, dict[str, Any]] = {}
    valid_targets: dict[str, pd.Series] = {}

    for target_name in TARGET_COLUMNS:
        selected_features = FEATURES_BY_TARGET[target_name]
        _, result, y_valid = evaluate_target(
            data=data,
            target_name=target_name,
            feature_columns=selected_features,
        )
        evaluation_metrics[target_name] = result
        valid_targets[target_name] = y_valid

        print(
            f"  - {target_name}: MAE={result['mae']:.6f} | "
            f"RMSE={result['rmse']:.6f} | R²={result['r2']:.6f} | "
            f"train={result['train_rows']:,} | test={result['test_rows']:,}"
        )

    print("[4/6] Melatih ulang pipeline deployment menggunakan seluruh data valid...")
    deployment_models: dict[str, Pipeline] = {}
    thresholds: dict[str, dict[str, float]] = {}
    deployment_rows: dict[str, int] = {}

    for target_name in TARGET_COLUMNS:
        selected_features = FEATURES_BY_TARGET[target_name]
        y_all = valid_targets[target_name]
        X_all = data.loc[y_all.index, selected_features].copy()

        final_pipeline = build_pipeline()
        final_pipeline.fit(X_all, y_all)
        deployment_models[target_name] = final_pipeline

        # Relative AirSense categories only; these are not official ISPU limits.
        thresholds[target_name] = {
            "q33": float(y_all.quantile(1 / 3)),
            "q66": float(y_all.quantile(2 / 3)),
        }
        deployment_rows[target_name] = int(len(y_all))

        print(
            f"  - {target_name}: final fit menggunakan {len(y_all):,} baris "
            f"dan {len(selected_features)} fitur"
        )

    print("[5/6] Menyimpan model dan metadata...")
    trained_at = datetime.now(timezone.utc).isoformat()
    bundle: dict[str, Any] = {
        "models": deployment_models,
        "thresholds": thresholds,
        # Keep this global list for API validation / the eight-field form.
        "feature_columns": INPUT_FEATURE_COLUMNS,
        # The inference API MUST use this mapping per target when constructing
        # the DataFrame passed to each fitted pipeline.
        "model_feature_columns": FEATURES_BY_TARGET,
        "target_columns": list(deployment_models.keys()),
        "category_definition": (
            "Kuantil 1/3 dan 2/3 dari seluruh target valid yang digunakan untuk "
            "fit pipeline deployment per target. Kategori relatif AirSense, "
            "bukan ISPU atau ambang kesehatan resmi."
        ),
        "dataset": "UCI Air Quality, dataset ID 360 (file CSV lokal)",
        "model_type": "RandomForestRegressor",
        "model_config": RANDOM_FOREST_CONFIG,
        "deployment_fit_rows": deployment_rows,
        "trained_at": trained_at,
        "artifact_version": 2,
    }
    joblib.dump(bundle, MODEL_PATH)

    metrics_payload: dict[str, Any] = {
        "dataset": "UCI Air Quality (ID 360, file CSV lokal)",
        "dataset_rows_after_blank_rows_removed": int(len(data)),
        "input_features": INPUT_FEATURE_COLUMNS,
        "model_feature_columns": FEATURES_BY_TARGET,
        "targets": evaluation_metrics,
        "category_note": (
            "Kategori Baik/Sedang/Buruk adalah kategori relatif AirSense "
            "berdasarkan kuantil target valid; bukan standar ISPU."
        ),
        "evaluation_split": (
            "Chronological 80:20 holdout per target. Metrik berasal dari model "
            "yang hanya dilatih pada 80% bagian awal. Artefak deployment "
            "kemudian di-fit ulang menggunakan seluruh baris target valid."
        ),
        "deployment_fit_rows": deployment_rows,
        "trained_at": trained_at,
        "artifact_version": 2,
    }
    METRICS_PATH.write_text(
        json.dumps(metrics_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[6/6] Training selesai.")
    print(f"Model tersimpan : {MODEL_PATH}")
    print(f"Metrik tersimpan: {METRICS_PATH}")
    print("Target tersedia :", ", ".join(deployment_models.keys()))
    print("Fitur per target:")
    for target_name, feature_columns in FEATURES_BY_TARGET.items():
        print(f"  - {target_name}: {', '.join(feature_columns)}")


if __name__ == "__main__":
    main()
