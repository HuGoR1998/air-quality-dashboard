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

# Shared feature contract between training (notebook) and inference (here).
FEATURE_COLUMNS = [
    "aqi_us",
    "temperature_c",
    "humidity",
    "pressure_hpa",
    "wind_speed_ms",
    "hour",
    "month",
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
    """Turn an AirQualityReading into the feature dict the models expect."""
    ts = reading.source_ts
    return {
        "aqi_us": reading.aqi_us,
        "temperature_c": reading.temperature_c,
        "humidity": reading.humidity,
        "pressure_hpa": reading.pressure_hpa,
        "wind_speed_ms": reading.wind_speed_ms,
        "hour": ts.hour if ts else 0,
        "month": ts.month if ts else 0,
    }


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
