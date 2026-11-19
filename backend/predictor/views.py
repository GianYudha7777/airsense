
import json
from functools import lru_cache

import joblib
import pandas as pd
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import PredictionInputSerializer


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

INPUT_TO_FEATURE = {
    "sensor_s1": "PT08.S1(CO)",
    "sensor_s2": "PT08.S2(NMHC)",
    "sensor_s3": "PT08.S3(NOx)",
    "sensor_s4": "PT08.S4(NO2)",
    "sensor_s5": "PT08.S5(O3)",
    "temperature": "T",
    "relative_humidity": "RH",
    "absolute_humidity": "AH",
}

TARGET_DETAILS = {
    "CO(GT)": {
        "label": "Karbon monoksida (CO)",
        "unit": "mg/m³",
    },
    "C6H6(GT)": {
        "label": "Benzena (C6H6)",
        "unit": "µg/m³",
    },
    "NOx(GT)": {
        "label": "Total nitrogen oksida (NOx)",
        "unit": "ppb",
    },
    "NO2(GT)": {
        "label": "Nitrogen dioksida (NO₂)",
        "unit": "µg/m³",
    },
}

CATEGORY_ORDER = {
    "Baik": 0,
    "Sedang": 1,
    "Buruk": 2,
}


@lru_cache(maxsize=1)
def load_model_bundle():
    """Memuat artefak ML satu kali selama proses Django berjalan."""
    path = settings.AIR_QUALITY_MODEL_PATH

    if not path.exists():
        return None

    bundle = joblib.load(path)

    # Pastikan artefak menggunakan struktur versi terbaru.
    required_keys = {
        "models",
        "thresholds",
        "feature_columns",
        "model_feature_columns",
        "target_columns",
        "artifact_version",
    }

    missing_keys = required_keys.difference(bundle.keys())

    if missing_keys:
        raise ValueError(
            f"Struktur artefak tidak lengkap: {sorted(missing_keys)}"
        )

    if bundle["artifact_version"] != 2:
        raise ValueError(
            f"Versi artefak tidak didukung: {bundle['artifact_version']}"
        )

    return bundle


def classify_relative(value, thresholds):
    """Klasifikasi relatif AirSense, bukan standar ISPU."""
    q_low = float(thresholds["q33"])
    q_high = float(thresholds["q66"])

    if value <= q_low:
        return "Baik"

    if value <= q_high:
        return "Sedang"

    return "Buruk"


@api_view(["GET"])
def health(request):
    try:
        bundle = load_model_bundle()

        ready = bundle is not None

        return Response({
            "status": "ok",
            "model_ready": ready,
            "artifact_version": (
                bundle["artifact_version"] if ready else None
            ),
            "available_targets": (
                bundle["target_columns"] if ready else []
            ),
            "message": (
                "Model AirSense siap digunakan."
                if ready
                else "Model belum tersedia."
            ),
        })

    except Exception as exc:
        return Response(
            {
                "status": "error",
                "model_ready": False,
                "detail": str(exc),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def metrics(request):
    path = settings.AIR_QUALITY_METRICS_PATH

    if not path.exists():
        return Response(
            {
                "detail": "Metrik belum tersedia."
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return Response(data)


@api_view(["POST"])
def predict(request):
    serializer = PredictionInputSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        bundle = load_model_bundle()

    except Exception as exc:
        return Response(
            {
                "detail": f"Gagal memuat model: {exc}"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if bundle is None:
        return Response(
            {
                "detail": "Model belum tersedia."
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    payload = serializer.validated_data

    # Konversi delapan input API menjadi nama fitur dataset UCI.
    input_values = {
        INPUT_TO_FEATURE[input_name]: value
        for input_name, value in payload.items()
    }

    predictions = []

    for target_name in bundle["target_columns"]:
        model = bundle["models"][target_name]

        # Ambil fitur yang memang digunakan oleh model target tersebut.
        selected_features = bundle["model_feature_columns"][target_name]

        if not set(selected_features).issubset(input_values):
            return Response(
                {
                    "detail": (
                        f"Konfigurasi fitur tidak valid untuk {target_name}."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Setiap model mendapatkan DataFrame sesuai fitur training-nya.
        input_frame = pd.DataFrame(
            [
                {
                    feature: input_values[feature]
                    for feature in selected_features
                }
            ],
            columns=selected_features,
        )

        if model.n_features_in_ != len(selected_features):
            return Response(
                {
                    "detail": (
                        f"Jumlah fitur model {target_name} tidak sesuai "
                        "dengan metadata artefak."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        value = float(model.predict(input_frame)[0])

        thresholds = bundle["thresholds"][target_name]
        category = classify_relative(value, thresholds)
        details = TARGET_DETAILS[target_name]

        predictions.append({
            "key": target_name,
            "label": details["label"],
            "value": round(value, 3),
            "unit": details["unit"],
            "category": category,
            "features_used": selected_features,
        })

    overall_category = max(
        (item["category"] for item in predictions),
        key=lambda category: CATEGORY_ORDER[category],
    )

    return Response({
        "overall_category": overall_category,
        "classification_note": (
            "Kategori Baik/Sedang/Buruk merupakan kategori relatif "
            "berdasarkan kuantil data training AirSense, bukan ISPU resmi."
        ),
        "predictions": predictions,
    })
