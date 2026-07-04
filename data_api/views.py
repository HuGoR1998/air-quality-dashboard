from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from .models import AirQualityReading
from .services import fetch_and_store_all


@login_required
def readings(request):
    qs = AirQualityReading.objects.all()
    selected_city = request.GET.get("city", "")
    if selected_city:
        qs = qs.filter(city=selected_city)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    cities = AirQualityReading.objects.values_list("city", flat=True).distinct().order_by("city")

    return render(request, "data_api/readings.html", {
        "active": "readings",
        "page": page,
        "cities": cities,
        "selected_city": selected_city,
    })


@login_required
def fetch_now(request):
    """Manually trigger a live fetch (handy for the demo)."""
    if request.method == "POST":
        summary = fetch_and_store_all()
        messages.success(
            request,
            f"Fetched {len(summary['created'])} reading(s); {len(summary['errors'])} error(s).",
        )
    return redirect("data_api:readings")
