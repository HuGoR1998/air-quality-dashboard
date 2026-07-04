"""DRF endpoints (Guideline 3.6).

Three endpoints:
  GET  /api/readings/     -> current + historical air-quality readings
  GET  /api/predictions/  -> stored ML predictions
  POST /api/predict/      -> feed current data, system returns a fresh prediction
"""

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from data_api.models import AirQualityReading
from dashboard.insights import get_enrichment, health_advisory
from predictor import services as predictor_services
from predictor.models import Prediction

from .serializers import AirQualityReadingSerializer, PredictionSerializer


@api_view(["GET"])
def api_root(request, format=None):
    """Browsable index of the available API endpoints."""
    return Response({
        "readings": reverse("api:readings", request=request, format=format),
        "predictions": reverse("api:predictions", request=request, format=format),
        "predict": reverse("api:predict", request=request, format=format),
        "insights": reverse("api:insights", request=request, format=format) + "?city=Kigali",
        "stats": reverse("api:stats", request=request, format=format),
    })


@api_view(["GET"])
def stats(request, format=None):
    """Live totals for the dashboard counter (readings, predictions, last fetch)."""
    last = AirQualityReading.objects.order_by("-fetched_at").first()
    return Response({
        "readings": AirQualityReading.objects.count(),
        "predictions": Prediction.objects.count(),
        "last_fetch": last.fetched_at if last else None,
    })


class ReadingListAPIView(generics.ListAPIView):
    """Current + historical readings. Optional ?city= filter."""

    serializer_class = AirQualityReadingSerializer

    def get_queryset(self):
        qs = AirQualityReading.objects.all()
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__iexact=city)
        return qs


class PredictionListAPIView(generics.ListAPIView):
    """Prediction history. Optional ?city= filter."""

    serializer_class = PredictionSerializer

    def get_queryset(self):
        qs = Prediction.objects.all()
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__iexact=city)
        return qs


class PredictAPIView(APIView):
    """Feed current data and let the system make a prediction.

    Body (JSON), all optional:
      - reading_id: predict from a specific stored reading
      - city:       predict from the latest reading for that city
    With no body, predicts from the most recent reading overall.
    """

    def post(self, request):
        reading_id = request.data.get("reading_id")
        city = request.data.get("city")

        if reading_id:
            reading = get_object_or_404(AirQualityReading, pk=reading_id)
        else:
            qs = AirQualityReading.objects.all()
            if city:
                qs = qs.filter(city__iexact=city)
            reading = qs.first()  # newest (default ordering)
            if reading is None:
                return Response(
                    {"detail": "No readings available to predict from. Fetch data first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            predictions = predictor_services.predict_from_reading(reading, save=True)
        except predictor_services.ModelNotTrained as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(
            PredictionSerializer(predictions, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class InsightsAPIView(APIView):
    """Enriched view for one city: current AQI, pollutants, climate, forecast,
    history and health advisory. Combines our stored IQAir reading + latest ML
    prediction with keyless Open-Meteo enrichment.

    Query params: ?city=Kigali&range=24h|7d|30d
    """

    def get(self, request):
        cities = [loc["city"] for loc in settings.AQ_LOCATIONS]
        city = request.query_params.get("city") or (cities[0] if cities else "")
        time_range = request.query_params.get("range", "24h")

        lat, lon = settings.CITY_COORDS.get(city, (None, None))
        if lat is None:
            return Response(
                {"detail": f"Unknown city '{city}'. Known: {cities}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        latest = AirQualityReading.objects.filter(city=city).first()
        current_aqi = latest.aqi_us if latest else None

        pred_1h = Prediction.objects.filter(city=city, horizon_hours=1).first()
        pred_24h = Prediction.objects.filter(city=city, horizon_hours=24).first()

        enrichment = get_enrichment(city, lat, lon, time_range)

        return Response({
            "city": city,
            "coords": {"lat": lat, "lon": lon},
            "current": {
                "aqi_us": current_aqi,
                "category": latest.category if latest else "Unknown",
                "main_pollutant": latest.main_pollutant_us if latest else "",
                "temperature_c": latest.temperature_c if latest else None,
                "humidity": latest.humidity if latest else None,
                "source_ts": latest.source_ts if latest else None,
                "fetched_at": latest.fetched_at if latest else None,
            },
            "prediction": {
                "next_1h": pred_1h.predicted_aqi_us if pred_1h else None,
                "next_1h_category": pred_1h.predicted_category if pred_1h else "",
                "next_24h": pred_24h.predicted_aqi_us if pred_24h else None,
                "next_24h_category": pred_24h.predicted_category if pred_24h else "",
            },
            "advisory": health_advisory(current_aqi),
            "pollutants": enrichment["pollutants"],
            "climate": enrichment["climate"],
            "history": enrichment["history"],
            "forecast": enrichment["forecast"],
        })
