from rest_framework import serializers


class PredictionInputSerializer(serializers.Serializer):
    # Lima respons sensor kimia dari dataset UCI.
    sensor_s1 = serializers.FloatField(min_value=0)
    sensor_s2 = serializers.FloatField(min_value=0)
    sensor_s3 = serializers.FloatField(min_value=0)
    sensor_s4 = serializers.FloatField(min_value=0)
    sensor_s5 = serializers.FloatField(min_value=0)

    # Variabel lingkungan.
    temperature = serializers.FloatField(min_value=-30, max_value=60)
    relative_humidity = serializers.FloatField(min_value=0, max_value=100)
    absolute_humidity = serializers.FloatField(min_value=0)
