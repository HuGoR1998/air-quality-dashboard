from django.urls import path

from . import views

app_name = "data_api"

urlpatterns = [
    path("", views.readings, name="readings"),
    path("fetch/", views.fetch_now, name="fetch_now"),
]
