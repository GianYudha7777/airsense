from rest_framework import serializers


ALLOWED_CHART_KEYS = (
    "prediction_distribution",
    "r2_comparison",
    "data_split",
    "feature_usage",
)

EXPECTED_TARGETS = {"CO(GT)", "C6H6(GT)", "NOx(GT)", "NO2(GT)"}


class PredictionChartItemSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=sorted(EXPECTED_TARGETS))
    label = serializers.CharField(max_length=100)
    value = serializers.FloatField()
    unit = serializers.CharField(max_length=30)
    category = serializers.ChoiceField(choices=("Baik", "Sedang", "Buruk"))


class ExplainChartRequestSerializer(serializers.Serializer):
    chart_key = serializers.ChoiceField(choices=ALLOWED_CHART_KEYS)
    overall_category = serializers.ChoiceField(
        choices=("Baik", "Sedang", "Buruk"), required=False
    )
    predictions = PredictionChartItemSerializer(many=True, required=False)

    def validate(self, attrs):
        chart_key = attrs["chart_key"]

        if chart_key == "prediction_distribution":
            predictions = attrs.get("predictions")
            overall_category = attrs.get("overall_category")
            if not predictions or overall_category is None:
                raise serializers.ValidationError(
                    "Penjelasan distribusi prediksi membutuhkan overall_category dan predictions."
                )
            received_targets = [item["key"] for item in predictions]
            if len(predictions) != 4 or set(received_targets) != EXPECTED_TARGETS:
                raise serializers.ValidationError(
                    "Data grafik harus berisi tepat empat target AirSense tanpa duplikasi."
                )
        elif "predictions" in attrs or "overall_category" in attrs:
            raise serializers.ValidationError(
                "Data prediksi hanya boleh dikirim untuk chart_key prediction_distribution."
            )

        return attrs
