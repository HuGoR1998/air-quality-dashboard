from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="reports/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("reports/", views.reports, name="reports"),
    path("reports/export/predictions.csv", views.export_predictions_csv, name="export_predictions"),
    path("reports/export/readings.csv", views.export_readings_csv, name="export_readings"),
]
