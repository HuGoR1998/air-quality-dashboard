"""Load the trained ML models and generate predictions from live readings.

Models are trained offline in ml/train_model.ipynb and exported with joblib to
ml/artifacts/, one regressor + one classifier per forecast horizon:
    aqi_regressor_1h.joblib   aqi_classifier_1h.joblib    (+1 hour, persistence)
    aqi_regressor_24h.joblib  aqi_classifier_24h.joblib   (+24 hours, real forecast)

This module loads them lazily and degrades gracefully (raising ModelNotTrained)
until the notebook has produced them.

IMPORTANT: FEATURE_COLUMNS must match the feature order used in the notebook.
"""

import logging

import joblib
from django.conf import settings

from data_api.models import AirQualityReading
from .models import Prediction

logger = logging.getLogger(__name__)

ARTIFACT_DIR = settings.BASE_DIR / "ml" / "artifacts"
HORIZONS = [1, 24]

# City -> id. MUST match the CITY_ID mapping in ml/_build_notebook.py.
CITY_ID = {"Kigali": 0, "Delhi": 1}

# Shared feature contract between training (notebook) and inference (here).
# Order must match the notebook's FEATURES list exactly.
FEATURE_COLUMNS = [
    "aqi_us",
    "temperature_c",
    "humidity",
    "pressure_hpa",
    "wind_speed_ms",
    "hour",
    "month",
    "city_id",
    "aqi_lag_1",
    "aqi_lag_3",
    "aqi_lag_6",
    "aqi_lag_24",
    "aqi_roll6",
    "aqi_trend3",
]

_models = {}  # horizon -> (regressor, classifier)
_loaded = False


class ModelNotTrained(Exception):
    """Raised when no trained model artifact is available yet."""


def _paths(horizon):
    return (
        ARTIFACT_DIR / f"aqi_regressor_{horizon}h.joblib",
        ARTIFACT_DIR / f"aqi_classifier_{horizon}h.joblib",
    )


def load_models(force=False):
    """Load joblib artifacts for every horizon into the module cache (once)."""
    global _loaded
    if _loaded and not force:
        return
    _models.clear()
    for horizon in HORIZONS:
        reg_path, clf_path = _paths(horizon)
        regressor = joblib.load(reg_path) if reg_path.exists() else None
        classifier = joblib.load(clf_path) if clf_path.exists() else None
        if regressor is not None or classifier is not None:
            _models[horizon] = (regressor, classifier)
    _loaded = True
    logger.info("Loaded models for horizons: %s", sorted(_models.keys()))


def models_available():
    load_models()
    return bool(_models)


def build_features(reading):
    """Build the feature dict the models expect: base + city + lag/trend features.

    The lag/trend features come from Open-Meteo's recent hourly AQI series for the
    city — the same source the model was trained on, and it has full history on
    demand (no cold-start). If Open-Meteo is unavailable we fall back to persistence
    (lags = current value) so predictions never crash.
    """
    ts = reading.source_ts
    city = reading.city
    current = reading.aqi_us or 0

    feats = {
        "aqi_us": reading.aqi_us,
        "temperature_c": reading.temperature_c,
        "humidity": reading.humidity,
        "pressure_hpa": reading.pressure_hpa,
        "wind_speed_ms": reading.wind_speed_ms,
        "hour": ts.hour if ts else 0,
        "month": ts.month if ts else 0,
        "city_id": CITY_ID.get(city, -1),
        # fallback = persistence (no trend) until real history is available
        "aqi_lag_1": current, "aqi_lag_3": current, "aqi_lag_6": current,
        "aqi_lag_24": current, "aqi_roll6": current, "aqi_trend3": 0,
    }

    lat, lon = settings.CITY_COORDS.get(city, (None, None))
    if lat is None:
        return feats

    try:
        from dashboard.insights import get_enrichment
        enr = get_enrichment(city, lat, lon, "7d")
        hist = [p["us_aqi"] for p in enr.get("history", []) if p.get("us_aqi") is not None]
        clim = enr.get("climate", {})
        if len(hist) >= 25:
            cur = hist[-1]
            feats.update({
                "aqi_us": cur,                        # Open-Meteo current (matches training)
                "aqi_lag_1": hist[-2],
                "aqi_lag_3": hist[-4],
                "aqi_lag_6": hist[-7],
                "aqi_lag_24": hist[-25],
                "aqi_roll6": sum(hist[-7:-1]) / 6.0,  # mean of the previous 6 hours
                "aqi_trend3": cur - hist[-4],         # slope over the last 3 hours
            })
            if clim.get("temperature_c") is not None:
                feats["temperature_c"] = clim.get("temperature_c")
                feats["humidity"] = clim.get("humidity")
                feats["pressure_hpa"] = clim.get("pressure_hpa")
                feats["wind_speed_ms"] = clim.get("wind_speed_ms")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo feature build failed for %s: %s", city, exc)

    return feats


def _vectorize(features):
    """Ordered feature row, coercing missing values to 0."""
    return [[float(features.get(col) or 0) for col in FEATURE_COLUMNS]]


def predict_from_reading(reading, save=True, horizons=None):
    """Generate a prediction per horizon from a reading.

    Returns a list of Prediction objects (one per available horizon).
    """
    load_models()
    if not _models:
        raise ModelNotTrained(
            "No trained model found. Run ml/train_model.ipynb to create the "
            "aqi_regressor_*h / aqi_classifier_*h files in ml/artifacts/."
        )

    horizons = horizons or sorted(_models.keys())
    features = build_features(reading)
    X = _vectorize(features)

    predictions = []
    for horizon in horizons:
        if horizon not in _models:
            continue
        regressor, classifier = _models[horizon]

        predicted_aqi = float(regressor.predict(X)[0]) if regressor is not None else None
        if classifier is not None:
            predicted_category = str(classifier.predict(X)[0])
        elif predicted_aqi is not None:
            predicted_category = AirQualityReading.category_for(int(round(predicted_aqi)))
        else:
            predicted_category = ""

        model_used = ", ".join(
            filter(
                None,
                [
                    type(regressor).__name__ if regressor is not None else "",
                    type(classifier).__name__ if classifier is not None else "",
                ],
            )
        )

        prediction = Prediction(
            reading=reading,
            city=reading.city,
            horizon_hours=horizon,
            predicted_aqi_us=predicted_aqi,
            predicted_category=predicted_category,
            model_used=model_used,
            input_features=features,
        )
        if save:
            prediction.save()
        predictions.append(prediction)

    return predictions
