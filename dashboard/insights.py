"""Open-Meteo enrichment for the dashboard.

IQAir (stored) remains the primary live/token source + our ML predictions.
This module adds *display-only* enrichment from the free, keyless Open-Meteo:
pollutant breakdown, climate/weather detail, an AQI forecast, and historical
trend windows. Results are cached briefly to avoid excess calls.
"""

import logging
from datetime import datetime

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://api.open-meteo.com/v1/forecast"

RANGE_DAYS = {"24h": 1, "7d": 7, "30d": 30}

# US EPA AQI health messaging per band.
_ADVICE = [
    (50, "Good", "Air quality is satisfactory, and air pollution poses little or no risk.", "None"),
    (100, "Moderate", "Air quality is acceptable. Unusually sensitive people should consider limiting prolonged outdoor exertion.", "Unusually sensitive individuals"),
    (150, "Unhealthy for Sensitive Groups", "Sensitive groups may experience health effects. The general public is less likely to be affected.", "Children, older adults, people with heart or lung disease"),
    (200, "Unhealthy", "Some of the general public may experience health effects; sensitive groups may experience more serious effects.", "Everyone, especially sensitive groups"),
    (300, "Very Unhealthy", "Health alert: the risk of health effects is increased for everyone.", "Everyone — avoid prolonged outdoor exertion"),
    (10**9, "Hazardous", "Health warning of emergency conditions: everyone is more likely to be affected.", "Everyone — avoid all outdoor activity"),
]


def health_advisory(aqi_us):
    if aqi_us is None:
        return {"category": "Unknown", "message": "No current reading available.", "at_risk": "—"}
    for upper, category, message, at_risk in _ADVICE:
        if aqi_us <= upper:
            return {"category": category, "message": message, "at_risk": at_risk}
    return {"category": "Hazardous", "message": _ADVICE[-1][2], "at_risk": _ADVICE[-1][3]}


def get_enrichment(city, lat, lon, time_range="24h"):
    """Return pollutant, climate, history and forecast data for a city."""
    time_range = time_range if time_range in RANGE_DAYS else "24h"
    cache_key = f"insights:{city}:{time_range}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    past_days = RANGE_DAYS[time_range]
    result = {"pollutants": {}, "climate": {}, "history": [], "forecast": []}

    try:
        aq = requests.get(AQ_URL, params={
            "latitude": lat, "longitude": lon,
            "current": "pm2_5,pm10,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,us_aqi,uv_index",
            "hourly": "us_aqi",
            "past_days": past_days, "forecast_days": 3, "timezone": "UTC",
        }, timeout=20).json()

        cur = aq.get("current", {})
        result["pollutants"] = {
            "pm2_5": cur.get("pm2_5"), "pm10": cur.get("pm10"), "ozone": cur.get("ozone"),
            "nitrogen_dioxide": cur.get("nitrogen_dioxide"), "sulphur_dioxide": cur.get("sulphur_dioxide"),
            "carbon_monoxide": cur.get("carbon_monoxide"), "us_aqi": cur.get("us_aqi"),
            "uv_index": cur.get("uv_index"),
        }

        # Split the hourly AQI series into history (past) and forecast (future).
        now = timezone.now().replace(tzinfo=None)
        hourly = aq.get("hourly", {})
        times = hourly.get("time", [])
        aqis = hourly.get("us_aqi", [])
        for t, a in zip(times, aqis):
            point = {"time": t, "us_aqi": a}
            try:
                is_future = datetime.fromisoformat(t) > now
            except ValueError:
                is_future = False
            (result["forecast"] if is_future else result["history"]).append(point)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo air-quality enrichment failed for %s: %s", city, exc)

    try:
        wx = requests.get(WX_URL, params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,"
                       "wind_direction_10m,cloud_cover,precipitation,uv_index",
            "wind_speed_unit": "ms", "timezone": "UTC",
        }, timeout=20).json()
        c = wx.get("current", {})
        result["climate"] = {
            "temperature_c": c.get("temperature_2m"), "humidity": c.get("relative_humidity_2m"),
            "pressure_hpa": c.get("surface_pressure"), "wind_speed_ms": c.get("wind_speed_10m"),
            "wind_direction": c.get("wind_direction_10m"), "cloud_cover": c.get("cloud_cover"),
            "precipitation": c.get("precipitation"), "uv_index": c.get("uv_index"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo weather enrichment failed for %s: %s", city, exc)

    cache.set(cache_key, result, 120)  # 2-minute cache
    return result
