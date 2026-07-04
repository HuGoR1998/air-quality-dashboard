from django.contrib import admin

from .models import AirQualityReading


@admin.register(AirQualityReading)
class AirQualityReadingAdmin(admin.ModelAdmin):
    list_display = (
        "city",
        "country",
        "aqi_us",
        "category",
        "main_pollutant_us",
        "temperature_c",
        "humidity",
        "source_ts",
        "fetched_at",
    )
    list_filter = ("city", "country")
    search_fields = ("city", "country")
    date_hierarchy = "fetched_at"
    readonly_fields = ("fetched_at",)

    @admin.display(description="Category")
    def category(self, obj):
        return obj.category
