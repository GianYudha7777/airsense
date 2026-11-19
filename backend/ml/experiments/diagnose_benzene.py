"""Diagnose error patterns for the AirSense benzene model.

Run from backend:
    python ml/diagnose_benzene.py

This script is read-only: it does not modify the dataset or model artifacts.
It repeats the one-sensor Random Forest walk-forward validation and reports
fold date ranges, target-range shifts, largest errors, and pooled metrics.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BASE_DIR / "ml" / "data" / "raw" / "AirQualityUCI.csv"

TARGET = "C6H6(GT)"
SENSOR = "PT08.S2(NMHC)"
FEATURE_COLUMNS = [
    "PT08.S1(CO)",
    "PT08.S2(NMHC)",
    "PT08.S3(NOx)",
    "PT08.S4(NO2)",
    "PT08.S5(O3)",
    "T",
    "RH",
    "AH",
]
NUMERIC_COLUMNS = FEATURE_COLUMNS + [TARGET]


def load_data() -> pd.DataFrame:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {DATASET_PATH}")

    data = pd.read_csv(
        DATASET_PATH,
        sep=";",
        decimal=",",
        encoding="latin1",
        usecols=["Date", "Time", *NUMERIC_COLUMNS],
        low_memory=False,
    )

    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data[NUMERIC_COLUMNS] = data[NUMERIC_COLUMNS].replace(-200, np.nan)
    # Match the row filtering used by the earlier benzene experiment:
    # remove rows where every selected model feature and the target are missing.
    data = data.dropna(subset=NUMERIC_COLUMNS, how="all").reset_index(drop=True)

    time_text = data["Time"].astype("string").str.strip().str.replace(
        ".", ":", regex=False
    )
    date_text = data["Date"].astype("string").str.strip()
    data["timestamp"] = pd.to_datetime(
        date_text + " " + time_text,
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )

    invalid_timestamps = int(data["timestamp"].isna().sum())
    if invalid_timestamps:
        examples = data.loc[data["timestamp"].isna(), ["Date", "Time"]].head(5)
        raise ValueError(
            f"Ada {invalid_timestamps} baris dengan timestamp tidak terbaca. "
            f"Contoh:\n{examples.to_string(index=False)}"
        )

    if not data["timestamp"].is_monotonic_increasing:
        bad_positions = data.index[data["timestamp"].diff() < pd.Timedelta(0)].tolist()[:10]
        raise ValueError(
            "Urutan Date/Time pada CSV tidak monoton naik. Jangan lanjutkan "
            "TimeSeriesSplit sebelum urutan waktu diperiksa. "
            f"Contoh posisi baris yang mundur: {bad_positions}"
        )

    return data


def make_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=220,
                    max_depth=18,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def main() -> None:
    print("[1/3] Memuat dan memeriksa urutan waktu dataset...")
    data = load_data()
    print(f"Baris setelah preprocessing: {len(data):,}")
    print(f"Rentang waktu: {data['timestamp'].min()} sampai {data['timestamp'].max()}")
    print("Urutan waktu: monoton naik")

    splitter = TimeSeriesSplit(n_splits=5)
    pooled_actual: list[float] = []
    pooled_predicted: list[float] = []

    print("\n[2/3] Mengulangi validasi 5-fold untuk Random Forest satu sensor...")
    for fold, (train_idx, test_idx) in enumerate(splitter.split(data), start=1):
        train_part = data.iloc[train_idx]
        test_part = data.iloc[test_idx]

        train_valid = train_part[TARGET].notna()
        test_valid = test_part[TARGET].notna()

        X_train = train_part.loc[train_valid, [SENSOR]]
        y_train = train_part.loc[train_valid, TARGET]
        X_test = test_part.loc[test_valid, [SENSOR]]
        y_test = test_part.loc[test_valid, TARGET]

        if len(y_train) < 100 or len(y_test) < 2:
            print(f"Fold {fold}: dilewati karena jumlah target valid tidak cukup")
            continue

        pipeline = make_pipeline()
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)

        mae = mean_absolute_error(y_test, predictions)
        rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
        r2 = r2_score(y_test, predictions)

        train_min, train_max = float(y_train.min()), float(y_train.max())
        below_train_range = int((y_test < train_min).sum())
        above_train_range = int((y_test > train_max).sum())

        print(f"\n--- Fold {fold} ---")
        print(
            f"Rentang test: {test_part['timestamp'].min()} sampai "
            f"{test_part['timestamp'].max()}"
        )
        print(
            f"Target train: min={train_min:.4f}, max={train_max:.4f} | "
            f"target test: min={y_test.min():.4f}, "
            f"median={y_test.median():.4f}, p95={y_test.quantile(0.95):.4f}, "
            f"max={y_test.max():.4f}"
        )
        print(
            f"Test di bawah rentang train: {below_train_range}/{len(y_test)} | "
            f"di atas rentang train: {above_train_range}/{len(y_test)}"
        )
        print(
            f"MAE={mae:.6f} | RMSE={rmse:.6f} | R2={r2:.6f} | "
            f"n_test={len(y_test)}"
        )

        errors = pd.DataFrame(
            {
                "timestamp": test_part.loc[test_valid, "timestamp"].to_numpy(),
                SENSOR: X_test[SENSOR].to_numpy(),
                "actual": y_test.to_numpy(),
                "predicted": predictions,
            }
        )
        errors["abs_error"] = (errors["actual"] - errors["predicted"]).abs()
        print("Kesalahan absolut terbesar (maksimal 3 baris):")
        print(
            errors.nlargest(3, "abs_error")
            .round(5)
            .to_string(index=False)
        )

        pooled_actual.extend(y_test.astype(float).tolist())
        pooled_predicted.extend(np.asarray(predictions, dtype=float).tolist())

    print("\n[3/3] Metrik gabungan seluruh observasi out-of-fold")
    if pooled_actual:
        pooled_mae = mean_absolute_error(pooled_actual, pooled_predicted)
        pooled_rmse = float(np.sqrt(mean_squared_error(pooled_actual, pooled_predicted)))
        pooled_r2 = r2_score(pooled_actual, pooled_predicted)
        print(f"Jumlah prediksi out-of-fold: {len(pooled_actual)}")
        print(f"Pooled MAE : {pooled_mae:.6f}")
        print(f"Pooled RMSE: {pooled_rmse:.6f}")
        print(f"Pooled R2  : {pooled_r2:.6f}")
    else:
        raise RuntimeError("Tidak ada prediksi valid yang dihasilkan.")

    print("\nSelesai. Dataset dan artefak model utama tidak diubah.")


if __name__ == "__main__":
    main()
