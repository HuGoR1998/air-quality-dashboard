from django.contrib import admin

from .models import Prediction


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "city",
        "horizon_hours",
        "predicted_aqi_us",
        "predicted_category",
        "model_used",
        "reading",
        "created_at",
    )
    list_filter = ("city", "horizon_hours", "predicted_category", "model_used")
    search_fields = ("city",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
