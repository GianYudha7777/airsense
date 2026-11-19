
"""Eksperimen validasi model prediksi Benzena AirSense.

Membandingkan:
- Dummy Regressor
- Linear Regression
- Random Forest Regressor

Feature set:
- Satu sensor PT08.S2(NMHC)
- Delapan fitur AirSense

Menggunakan 5-fold expanding time-series validation.
Script ini tidak mengubah artefak model utama.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BASE_DIR / "ml" / "data" / "raw" / "AirQualityUCI.csv"

TARGET = "C6H6(GT)"

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

FEATURE_SETS = {
    "1_sensor": ["PT08.S2(NMHC)"],
    "8_fitur": FEATURE_COLUMNS,
}

MODELS = {
    "Dummy": DummyRegressor(strategy="mean"),
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(
        n_estimators=220,
        max_depth=18,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    ),
}


def load_data():
    print("[1/3] Membaca dataset lokal...")

    columns = FEATURE_COLUMNS + [TARGET]

    data = pd.read_csv(
        DATASET_PATH,
        sep=";",
        decimal=",",
        encoding="latin1",
        usecols=columns,
    )

    for column in columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    data = data.replace(-200, np.nan)
    data = data.dropna(how="all").reset_index(drop=True)

    print("Jumlah baris:", len(data))

    return data


def main():
    data = load_data()

    splitter = TimeSeriesSplit(n_splits=5)
    results = []

    print("\n[2/3] Menjalankan eksperimen...")

    for feature_name, selected_features in FEATURE_SETS.items():

        for model_name, estimator in MODELS.items():

            print(f"\nModel: {model_name}")
            print(f"Fitur: {feature_name}")

            fold_number = 0

            for train_idx, test_idx in splitter.split(data):

                fold_number += 1

                train_data = data.iloc[train_idx]
                test_data = data.iloc[test_idx]

                # Target yang hilang tidak boleh digunakan untuk training
                # maupun penghitungan evaluasi.
                train_valid = train_data[TARGET].notna()
                test_valid = test_data[TARGET].notna()

                X_train = train_data.loc[
                    train_valid, selected_features
                ]
                y_train = train_data.loc[
                    train_valid, TARGET
                ]

                X_test = test_data.loc[
                    test_valid, selected_features
                ]
                y_test = test_data.loc[
                    test_valid, TARGET
                ]

                if len(y_train) < 100 or len(y_test) < 2:
                    print(f"  Fold {fold_number}: dilewati (data kurang)")
                    continue

                pipeline = Pipeline([
                    (
                        "imputer",
                        SimpleImputer(strategy="median"),
                    ),
                    (
                        "model",
                        clone(estimator),
                    ),
                ])

                pipeline.fit(X_train, y_train)
                predictions = pipeline.predict(X_test)

                mae = mean_absolute_error(
                    y_test, predictions
                )

                rmse = np.sqrt(
                    mean_squared_error(y_test, predictions)
                )

                r2 = r2_score(y_test, predictions)

                results.append({
                    "model": model_name,
                    "feature_set": feature_name,
                    "fold": fold_number,
                    "mae": mae,
                    "rmse": rmse,
                    "r2": r2,
                    "train_rows": len(y_train),
                    "test_rows": len(y_test),
                })

                print(
                    f"  Fold {fold_number}: "
                    f"MAE={mae:.6f} | "
                    f"RMSE={rmse:.6f} | "
                    f"R²={r2:.6f}"
                )

    if not results:
        raise RuntimeError("Tidak ada hasil eksperimen yang tersedia.")

    results_df = pd.DataFrame(results)

    print("\n[3/3] Ringkasan hasil eksperimen")

    summary = (
        results_df
        .groupby(["feature_set", "model"])
        .agg(
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .round(6)
    )

    print("\n", summary.to_string())

    print("\nJumlah fold per kombinasi:")
    print(
        results_df.groupby(
            ["feature_set", "model"]
        ).size()
    )

    print("\nEksperimen selesai.")
    print("Tidak ada model utama yang diubah.")


if __name__ == "__main__":
    main()
