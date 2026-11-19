"""Compare one-sensor and eight-feature Random Forest models for CO, NOx and NO2.

Run from backend:
    python ml/experiment_other_targets.py

The best single input feature is selected independently inside each training fold
using absolute Spearman correlation with that fold's training target only.
This avoids selecting features using held-out test observations. The script
reads the local UCI CSV and does not modify model artifacts.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BASE_DIR / "ml" / "data" / "raw" / "AirQualityUCI.csv"

SENSOR_COLUMNS = [
    "PT08.S1(CO)",
    "PT08.S2(NMHC)",
    "PT08.S3(NOx)",
    "PT08.S4(NO2)",
    "PT08.S5(O3)",
]
FEATURE_COLUMNS = SENSOR_COLUMNS + ["T", "RH", "AH"]
TARGETS = ["CO(GT)", "NOx(GT)", "NO2(GT)"]

ESTIMATOR = RandomForestRegressor(
    n_estimators=220,
    max_depth=18,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
)


def load_data() -> pd.DataFrame:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {DATASET_PATH}")

    required = ["Date", "Time", *FEATURE_COLUMNS, *TARGETS]
    data = pd.read_csv(
        DATASET_PATH,
        sep=";",
        decimal=",",
        encoding="latin1",
        usecols=required,
        low_memory=False,
    )

    for column in FEATURE_COLUMNS + TARGETS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data[FEATURE_COLUMNS + TARGETS] = data[FEATURE_COLUMNS + TARGETS].replace(-200, np.nan)
    data = data.dropna(subset=FEATURE_COLUMNS + TARGETS, how="all").reset_index(drop=True)

    time_text = data["Time"].astype("string").str.strip().str.replace(".", ":", regex=False)
    date_text = data["Date"].astype("string").str.strip()
    data["timestamp"] = pd.to_datetime(
        date_text + " " + time_text,
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )
    if data["timestamp"].isna().any():
        raise ValueError("Ada timestamp yang gagal dibaca dari kolom Date/Time.")
    if not data["timestamp"].is_monotonic_increasing:
        raise ValueError("Urutan waktu dataset tidak monoton naik; periksa Date/Time.")
    return data


def make_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", clone(ESTIMATOR)),
    ])


def select_single_feature_from_training(train_part: pd.DataFrame, target: str) -> str:
    """Select one input using training-only absolute Spearman correlation."""
    correlations: dict[str, float] = {}
    for feature in FEATURE_COLUMNS:
        pair = train_part[[feature, target]].dropna()
        if len(pair) < 30 or pair[feature].nunique() < 2 or pair[target].nunique() < 2:
            continue
        value = pair[feature].corr(pair[target], method="spearman")
        if pd.notna(value):
            correlations[feature] = abs(float(value))
    if not correlations:
        raise RuntimeError(f"Tidak dapat memilih fitur untuk target {target}.")
    return max(correlations, key=correlations.get)


def evaluate(
    train_part: pd.DataFrame,
    test_part: pd.DataFrame,
    target: str,
    features: list[str],
) -> dict[str, float | int]:
    train_valid = train_part[target].notna()
    test_valid = test_part[target].notna()
    X_train = train_part.loc[train_valid, features]
    y_train = train_part.loc[train_valid, target]
    X_test = test_part.loc[test_valid, features]
    y_test = test_part.loc[test_valid, target]

    if len(y_train) < 100 or len(y_test) < 2:
        raise RuntimeError(
            f"Data tidak cukup untuk {target}: train={len(y_train)}, test={len(y_test)}"
        )

    model = make_pipeline()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    return {
        "mae": float(mean_absolute_error(y_test, predictions)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "r2": float(r2_score(y_test, predictions)),
        "train_rows": int(len(y_train)),
        "test_rows": int(len(y_test)),
    }


def main() -> None:
    print("[1/3] Membaca dataset lokal dan memeriksa urutan waktu...")
    data = load_data()
    print(f"Baris setelah preprocessing: {len(data):,}")
    print(f"Rentang waktu: {data['timestamp'].min()} sampai {data['timestamp'].max()}")

    splitter = TimeSeriesSplit(n_splits=5)
    records: list[dict[str, object]] = []
    feature_choices: dict[str, list[str]] = {target: [] for target in TARGETS}

    print("\n[2/3] Membandingkan satu fitur terpilih dengan delapan fitur...")
    for target in TARGETS:
        print(f"\n========== TARGET: {target} ==========")
        for fold, (train_idx, test_idx) in enumerate(splitter.split(data), start=1):
            train_part = data.iloc[train_idx]
            test_part = data.iloc[test_idx]
            selected_feature = select_single_feature_from_training(train_part, target)
            feature_choices[target].append(selected_feature)

            one = evaluate(train_part, test_part, target, [selected_feature])
            eight = evaluate(train_part, test_part, target, FEATURE_COLUMNS)

            print(f"\nFold {fold} | fitur tunggal terpilih: {selected_feature}")
            for feature_set, result in (("1_fitur", one), ("8_fitur", eight)):
                records.append({"target": target, "fold": fold, "feature_set": feature_set,
                                "selected_feature": selected_feature if feature_set == "1_fitur" else "semua",
                                **result})
                print(
                    f"  {feature_set}: MAE={result['mae']:.6f} | "
                    f"RMSE={result['rmse']:.6f} | R2={result['r2']:.6f}"
                )

    results = pd.DataFrame(records)
    summary = (
        results.groupby(["target", "feature_set"])
        .agg(
            mae_mean=("mae", "mean"), mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"), rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"), r2_std=("r2", "std"),
        )
        .round(6)
    )

    print("\n[3/3] Ringkasan rata-rata lima fold")
    print(summary.to_string())
    print("\nFrekuensi fitur tunggal yang terpilih (seleksi hanya dari data training):")
    for target, choices in feature_choices.items():
        print(f"  {target}: {pd.Series(choices).value_counts().to_dict()}")

    print("\nSelesai. Dataset dan artefak model utama tidak diubah.")


if __name__ == "__main__":
    main()
