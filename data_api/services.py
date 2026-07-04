"""IQAir AirVisual API client + storage helpers (Guideline 3.2).

Keeps all external-API logic in one place: call the API with the token, verify
the response, parse it, and persist each reading. Used by both the
`fetch_air_quality` management command and the background scheduler.
"""

import logging

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, is_naive
from datetime import timezone as dt_timezone

from .models import AirQualityReading

logger = logging.getLogger(__name__)


class IQAirError(Exception):
    """Raised when the IQAir API call fails or returns a non-success payload."""


def _parse_ts(raw):
    """Parse an IQAir ISO timestamp (e.g. '2026-07-04T14:00:00.000Z') to aware UTC."""
    if not raw:
        return None
    dt = parse_datetime(raw.replace("Z", "+00:00"))
    if dt is not None and is_naive(dt):
        dt = make_aware(dt, dt_timezone.utc)
    return dt


def fetch_city(city, state, country, timeout=10):
    """Call GET /v2/city and return the raw `data` dict. Raises IQAirError on failure."""
    if not settings.AIRVISUAL_API_KEY:
        raise IQAirError("AIRVISUAL_API_KEY is not set (check your .env file).")

    url = f"{settings.AIRVISUAL_BASE_URL}/city"
    params = {
        "city": city,
        "state": state,
        "country": country,
        "key": settings.AIRVISUAL_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        raise IQAirError(f"Timeout contacting IQAir for {city}.")
    except requests.exceptions.RequestException as exc:
        raise IQAirError(f"Network error contacting IQAir for {city}: {exc}")

    # Guideline 3.2.3 — verify the response code before processing.
    if resp.status_code != 200:
        raise IQAirError(f"IQAir returned HTTP {resp.status_code} for {city}: {resp.text[:200]}")

    payload = resp.json()
    if payload.get("status") != "success":
        raise IQAirError(f"IQAir status != success for {city}: {payload}")

    return payload["data"]


def parse_reading(data):
    """Map an IQAir `data` dict to AirQualityReading field values."""
    current = data.get("current", {})
    pollution = current.get("pollution", {})
    weather = current.get("weather", {})
    return {
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "country": data.get("country", ""),
        "aqi_us": pollution.get("aqius"),
        "aqi_cn": pollution.get("aqicn"),
        "main_pollutant_us": pollution.get("mainus", ""),
        "main_pollutant_cn": pollution.get("maincn", ""),
        "source_ts": _parse_ts(pollution.get("ts")),
        "temperature_c": weather.get("tp"),
        "humidity": weather.get("hu"),
        "pressure_hpa": weather.get("pr"),
        "wind_speed_ms": weather.get("ws"),
        "wind_direction": weather.get("wd"),
        "weather_icon": weather.get("ic", ""),
    }


def fetch_and_store_all():
    """Fetch every configured location and persist a reading for each.

    Returns {"created": [AirQualityReading, ...], "errors": [str, ...]} so callers
    (command / scheduler) can report cleanly without crashing on a single failure.
    """
    created, errors = [], []
    for loc in settings.AQ_LOCATIONS:
        try:
            data = fetch_city(loc["city"], loc["state"], loc["country"])
            fields = parse_reading(data)
            reading = AirQualityReading.objects.create(**fields)
            created.append(reading)
            logger.info("Stored reading for %s (AQI US=%s)", reading.city, reading.aqi_us)
        except Exception as exc:  # noqa: BLE001 — collect and continue
            msg = f"{loc.get('city', '?')}: {exc}"
            errors.append(msg)
            logger.warning("Failed to fetch %s", msg)
    return {"created": created, "errors": errors}
