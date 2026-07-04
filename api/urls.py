from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("", views.api_root, name="root"),
    path("readings/", views.ReadingListAPIView.as_view(), name="readings"),
    path("predictions/", views.PredictionListAPIView.as_view(), name="predictions"),
    path("predict/", views.PredictAPIView.as_view(), name="predict"),
    path("insights/", views.InsightsAPIView.as_view(), name="insights"),
    path("stats/", views.stats, name="stats"),
]
