"""URL configuration for the Air Quality Prediction Dashboard project."""

from django.contrib import admin
from django.urls import include, path

# Brand the built-in Django admin so it looks part of the project.
admin.site.site_header = "AirWatch RW Administration"
admin.site.site_title = "AirWatch RW Admin"
admin.site.index_title = "Air Quality Data & Predictions"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),

    # App pages
    path("", include("dashboard.urls")),        # /            -> dashboard
    path("readings/", include("data_api.urls")),  # /readings/   -> live readings
    path("predictions/", include("predictor.urls")),  # /predictions/ -> ML predictions
    path("", include("reports.urls")),          # /login/ /logout/ /reports/
]
