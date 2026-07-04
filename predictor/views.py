from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Prediction
from .services import models_available


@login_required
def predictions(request):
    qs = Prediction.objects.all()
    selected_city = request.GET.get("city", "")
    horizon = request.GET.get("horizon", "")
    if selected_city:
        qs = qs.filter(city=selected_city)
    if horizon:
        qs = qs.filter(horizon_hours=horizon)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    cities = Prediction.objects.values_list("city", flat=True).distinct().order_by("city")

    return render(request, "predictor/predictions.html", {
        "active": "predictions",
        "page": page,
        "cities": cities,
        "selected_city": selected_city,
        "horizon": horizon,
        "models_ready": models_available(),
    })
