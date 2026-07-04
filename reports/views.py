import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from data_api.models import AirQualityReading
from predictor.models import Prediction


@login_required
def reports(request):
    context = {
        "active": "reports",
        "total_readings": AirQualityReading.objects.count(),
        "total_predictions": Prediction.objects.count(),
        "recent_predictions": Prediction.objects.all()[:15],
        "first_reading": AirQualityReading.objects.order_by("fetched_at").first(),
        "last_reading": AirQualityReading.objects.order_by("-fetched_at").first(),
    }
    return render(request, "reports/reports.html", context)


@login_required
def export_predictions_csv(request):
    """Download the full prediction log as CSV (Guideline 3.1 — reports app)."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="predictions_log.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "created_at_utc", "city", "horizon_hours",
        "predicted_aqi_us", "predicted_category", "model_used",
    ])
    for p in Prediction.objects.all().iterator():
        writer.writerow([
            p.created_at.isoformat(), p.city, p.horizon_hours,
            p.predicted_aqi_us, p.predicted_category, p.model_used,
        ])
    return response


@login_required
def export_readings_csv(request):
    """Download the full readings log as CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="readings_log.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "fetched_at_utc", "source_ts_utc", "city", "country",
        "aqi_us", "aqi_cn", "main_pollutant_us",
        "temperature_c", "humidity", "pressure_hpa", "wind_speed_ms",
    ])
    for r in AirQualityReading.objects.all().iterator():
        writer.writerow([
            r.fetched_at.isoformat(), r.source_ts.isoformat(), r.city, r.country,
            r.aqi_us, r.aqi_cn, r.main_pollutant_us,
            r.temperature_c, r.humidity, r.pressure_hpa, r.wind_speed_ms,
        ])
    return response
