# How We Built It — Full Walkthrough

We built a Django web application that monitors air quality in real time, stores it in
PostgreSQL, forecasts future AQI with machine learning, and presents everything on a live
dashboard backed by a REST API. We split the work into three areas — the data/back-end
pipeline, the machine-learning layer, and the front-end/API layer — while keeping a shared
understanding of the whole system.

---

## 1. Back-end, Data & Database

We set up the Django project (`config/`) and created a **five-app MVT architecture** so each
concern is isolated: `data_api` (external data), `predictor` (ML), `dashboard` (UI), `reports`
(auth + exports) and `api` (REST layer). We configured `settings.py` to load every secret — the
API key and the database password — from a `.env` file using `python-dotenv`, and set up
namespaced URL routing across the apps.

For the live data we integrated the **IQAir AirVisual API** in `data_api/services.py`. We use
`requests` to call the `/v2/city` endpoint with our API token, verify the response
(`status_code == 200`) before using it, and handle timeouts, network errors and invalid tokens
gracefully so one failure never crashes the app. We map IQAir's JSON onto our own fields in
`parse_reading()`.

We designed the **`AirQualityReading` model**, generated migrations, and connected Django to a
**PostgreSQL** database (`air_quality_db`). Every fetch inserts a new row carrying both the source
timestamp and our own `fetched_at` timestamp.

To make the data live, we implemented an **APScheduler background job** in `data_api/scheduler.py`.
It runs **every five minutes** (interval from `.env`), fetches all configured cities, stores each
reading, then triggers a prediction on every new one. It starts automatically with the server
(`data_api/apps.py`). We also added a management command and a **"Fetch now"** button that call the
same code, plus the README, requirements.txt and setup docs.

## 2. Machine Learning

We collected **historical training data** — twelve months of hourly air-quality and weather
readings for Kigali and Delhi — from the free Open-Meteo archive, saved under `ml/data/`.

In **`ml/train_model.ipynb`** we did feature engineering (current AQI, temperature, humidity,
pressure, wind speed, hour, month, **city**, plus **lag/trend features** — the recent AQI history
and slope) and created **two forecast targets**: AQI one hour ahead and twenty-four hours ahead.
For each horizon we trained a RandomForest **regressor** (the AQI value) and a RandomForest
**classifier** (the category band), evaluated with RMSE/MAE/R² and accuracy/F1. We kept both
horizons to show the contrast: +1h is essentially a **persistence baseline**, while **+24h is a
genuine forecast** (R² ≈ 0.87 after adding the trend features). We exported the four models with
**joblib** to `ml/artifacts/`.

We then wrote the **`predictor` app** (`predictor/services.py`): it loads the four models once,
builds the feature vector (including lag/trend features from the recent hourly series) for the
latest live reading, runs both models per horizon, and saves a **`Prediction`** row (city, horizon,
predicted AQI, category, model used, input snapshot, timestamp). It fails gracefully if the models
aren't trained yet.

We also built the **Open-Meteo enrichment service** in `dashboard/insights.py`. Because IQAir's
free tier returns only a single AQI value, we use Open-Meteo (free, keyless) to add the **pollutant
breakdown** (PM2.5, PM10, O₃, NO₂, SO₂, CO), full **climate** detail (UV, cloud, precipitation, wind
direction), a real multi-day **forecast**, and historical trend windows. We wrote the
**health-advisory** logic here too — an EPA-based table turning the current AQI into a category, a
message and a "who's at risk" note — cached for two minutes.

## 3. Front-end, Dashboard & API

We built the dashboard as a **single-page "command center"** using Bootstrap 5 and a small custom
stylesheet, with the libraries vendored locally so the demo works offline. The layout
(`templates/base.html`) has a sidebar, navbar and a **light/dark theme toggle**. The main page
shows, per city, a live counter, an **AQI gauge**, an interactive **map**, a **health-advisory**
card, a **pollutant-breakdown** chart, a **climate** panel with a wind compass, and an **AQI
trend-and-forecast** chart, plus a range selector and alert banner.

For visualizations we used **Chart.js** (gauge, pollutant bar, and the trend/forecast line chart
overlaying history, provider forecast and our ML prediction) and **Leaflet** for the map, drawing
each city as an AQI-coloured marker. The page pulls data from our API on a timer and re-renders
without reloading.

We built the **REST API layer** with Django REST Framework in the `api` app — serializers and views
for `/readings/`, `/predictions/`, `/predict/`, `/insights/` and `/stats/` — and exported a
**Postman collection** for GET/POST testing.

Finally we built the **`reports` app** for **user authentication** (login/logout) and **CSV export**
of the readings and predictions logs.

## In short — how the pieces connect
The scheduler fetches from IQAir every five minutes and stores each reading in PostgreSQL; the
predictor turns each new reading into a forecast and stores that too; the REST API exposes both; and
the dashboard reads the API to draw its live charts, map and advisory, enriched with extra detail
from Open-Meteo. **IQAir is our primary token-based live source; Open-Meteo provides the training
history and the display-only enrichment.**
