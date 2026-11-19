from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .ai_serializers import ExplainChartRequestSerializer
from .ai_service import (
    GroqExplanationError,
    GroqNotConfiguredError,
    generate_chart_explanation,
)


class AirSenseAIExplainThrottle(AnonRateThrottle):
    """Limit anonymous AI calls to avoid accidental API usage/cost spikes."""
    rate = "20/hour"


def _read_metrics() -> dict:
    path = settings.AIR_QUALITY_METRICS_PATH
    if not Path(path).is_file():
        raise FileNotFoundError("Metrik model belum tersedia. Jalankan training ML terlebih dahulu.")
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _build_evaluation_context(chart_key: str) -> dict:
    metrics = _read_metrics()
    targets = metrics.get("targets", {})
    labels = {
        "CO(GT)": "Karbon monoksida (CO)",
        "C6H6(GT)": "Benzena (C6H6)",
        "NOx(GT)": "Oksida nitrogen (NOx)",
        "NO2(GT)": "Nitrogen dioksida (NO2)",
    }
    feature_map = metrics.get("model_feature_columns", {})
    rows = []

    for target_key in labels:
        item = targets.get(target_key)
        if not item:
            continue
        features = item.get("feature_columns") or feature_map.get(target_key, [])
        rows.append({
            "target": target_key,
            "nama": labels[target_key],
            "mae": item.get("mae"),
            "rmse": item.get("rmse"),
            "r2": item.get("r2"),
            "data_latih": item.get("train_rows"),
            "data_uji": item.get("test_rows"),
            "jumlah_fitur": len(features),
            "fitur": features,
        })

    if len(rows) != 4:
        raise ValueError("Metrics.json belum memuat evaluasi lengkap empat target AirSense.")

    if chart_key == "r2_comparison":
        return {
            "metode_evaluasi": metrics.get("evaluation_method") or metrics.get("evaluation_split") or "pemisahan kronologis 80:20",
            "target": [
                {"nama": row["nama"], "r2": row["r2"], "mae": row["mae"], "rmse": row["rmse"]}
                for row in rows
            ],
        }

    if chart_key == "data_split":
        return {
            "metode_evaluasi": metrics.get("evaluation_method") or metrics.get("evaluation_split") or "pemisahan kronologis 80:20",
            "target": [
                {"nama": row["nama"], "data_latih": row["data_latih"], "data_uji": row["data_uji"]}
                for row in rows
            ],
        }

    if chart_key == "feature_usage":
        return {
            "target": [
                {"nama": row["nama"], "jumlah_fitur": row["jumlah_fitur"], "fitur": row["fitur"]}
                for row in rows
            ],
        }

    raise ValueError("Jenis grafik evaluasi tidak dikenal.")


@api_view(["POST"])
@throttle_classes([AirSenseAIExplainThrottle])
def explain_chart(request):
    serializer = ExplainChartRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    payload = serializer.validated_data
    chart_key = payload["chart_key"]

    try:
        if chart_key == "prediction_distribution":
            chart_data = {
                "kategori_keseluruhan": payload["overall_category"],
                "catatan_kategori": (
                    "Kategori relatif per polutan berdasarkan kuantil data latih AirSense, bukan ISPU resmi."
                ),
                "prediksi": payload["predictions"],
                "jumlah_polutan": len(payload["predictions"]),
                "jumlah_per_kategori": {
                    category: sum(1 for item in payload["predictions"] if item["category"] == category)
                    for category in ("Baik", "Sedang", "Buruk")
                },
            }
        else:
            chart_data = _build_evaluation_context(chart_key)

        explanation, model = generate_chart_explanation(chart_key, chart_data)
        return Response({
            "chart_key": chart_key,
            "model": model,
            "explanation": explanation,
            "generated_at": timezone.now().isoformat(),
        })

    except GroqNotConfiguredError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except FileNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except GroqExplanationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
