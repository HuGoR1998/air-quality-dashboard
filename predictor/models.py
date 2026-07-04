from django.db import models


class Prediction(models.Model):
    """A stored ML prediction (Guideline 3.4.11 + 3.3).

    Each record keeps: a reference to the input reading, an input snapshot,
    the predicted value(s), the model used, and a timestamp.
    """

    # Reference to the reading the prediction was made from (input reference).
    reading = models.ForeignKey(
        "data_api.AirQualityReading",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="predictions",
    )
    city = models.CharField(max_length=100)
    horizon_hours = models.IntegerField(default=24, help_text="Forecast horizon in hours (e.g. 1 or 24)")

    # Predicted values (regression + classification).
    predicted_aqi_us = models.FloatField(null=True, blank=True, help_text="Forecast next US AQI")
    predicted_category = models.CharField(max_length=50, blank=True, help_text="Predicted pollution band")

    # Provenance.
    model_used = models.CharField(max_length=120, blank=True)
    input_features = models.JSONField(default=dict, blank=True, help_text="Input snapshot used for the prediction")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city", "-created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.city} +{self.horizon_hours}h pred AQI={self.predicted_aqi_us} "
            f"({self.predicted_category}) @ {self.created_at:%Y-%m-%d %H:%M}"
        )
