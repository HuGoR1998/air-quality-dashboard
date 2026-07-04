from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """Single-page 'command center'. All live data is loaded client-side from
    /api/insights/ (which merges IQAir + our ML + Open-Meteo enrichment)."""
    cities = [
        {"city": loc["city"], "lat": loc.get("lat"), "lon": loc.get("lon")}
        for loc in settings.AQ_LOCATIONS
    ]
    return render(request, "dashboard/home.html", {"active": "home", "cities": cities})
