from rest_framework import serializers

from data_api.models import AirQualityReading
from predictor.models import Prediction


class AirQualityReadingSerializer(serializers.ModelSerializer):
    category = serializers.CharField(read_only=True)

    class Meta:
        model = AirQualityReading
        fields = [
            "id",
            "city",
            "state",
            "country",
            "aqi_us",
            "aqi_cn",
            "category",
            "main_pollutant_us",
            "temperature_c",
            "humidity",
            "pressure_hpa",
            "wind_speed_ms",
            "wind_direction",
            "weather_icon",
            "source_ts",
            "fetched_at",
        ]


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = [
            "id",
            "city",
            "horizon_hours",
            "reading",
            "predicted_aqi_us",
            "predicted_category",
            "model_used",
            "input_features",
            "created_at",
        ]
