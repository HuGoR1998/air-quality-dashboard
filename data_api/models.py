from django.db import models


class AirQualityReading(models.Model):
    """A single air-quality snapshot fetched from the IQAir AirVisual API.

    One row is stored per fetch (Guideline 3.2.5 — persist every reading with a
    timestamp). `source_ts` is the reading time reported by IQAir; `fetched_at`
    is when our scheduler pulled it.
    """

    # --- Location ---
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    # --- Pollution ---
    aqi_us = models.IntegerField(null=True, blank=True, help_text="US AQI")
    aqi_cn = models.IntegerField(null=True, blank=True, help_text="China AQI")
    main_pollutant_us = models.CharField(max_length=10, blank=True)
    main_pollutant_cn = models.CharField(max_length=10, blank=True)

    # --- Weather (accompanies the pollution reading) ---
    temperature_c = models.FloatField(null=True, blank=True)
    humidity = models.IntegerField(null=True, blank=True, help_text="Relative humidity %")
    pressure_hpa = models.IntegerField(null=True, blank=True)
    wind_speed_ms = models.FloatField(null=True, blank=True)
    wind_direction = models.IntegerField(null=True, blank=True, help_text="Degrees")
    weather_icon = models.CharField(max_length=10, blank=True)

    # --- Timestamps ---
    source_ts = models.DateTimeField(help_text="Reading time reported by IQAir (UTC)")
    fetched_at = models.DateTimeField(auto_now_add=True, help_text="When our system fetched it")

    class Meta:
        ordering = ["-fetched_at"]
        indexes = [
            models.Index(fields=["city", "source_ts"]),
            models.Index(fields=["-fetched_at"]),
        ]

    def __str__(self):
        return f"{self.city} AQI(US)={self.aqi_us} @ {self.source_ts:%Y-%m-%d %H:%M}"

    # US AQI category bands (upper bound inclusive, label)
    AQI_BANDS = [
        (50, "Good"),
        (100, "Moderate"),
        (150, "Unhealthy for Sensitive Groups"),
        (200, "Unhealthy"),
        (300, "Very Unhealthy"),
        (10_000, "Hazardous"),
    ]

    @staticmethod
    def category_for(aqi_us):
        if aqi_us is None:
            return "Unknown"
        for upper, label in AirQualityReading.AQI_BANDS:
            if aqi_us <= upper:
                return label
        return "Hazardous"

    @property
    def category(self):
        return self.category_for(self.aqi_us)
