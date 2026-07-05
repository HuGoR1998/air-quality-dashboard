# Assignment — Point-by-Point Answers (mirrors the brief exactly)

For each requirement in Section 3 + the Marking Scheme: **what we did · file(s) · link(s) · code
reference · logic.**

---

# 3. Mandatory Technical Architecture

## 3.1 Project-Level Structure (MVT)

**• "One Django project containing at least 3 separate apps (4th DRF app recommended); proper MVT
separation; no business logic inside templates."**
→ One project (`config/`) with **5 apps**. Business logic lives in views/services, never in templates
(templates only display context). ✅ (3 required + dashboard + DRF app.)

**• "A project-level dashboard base template on AdminLTE/Bootstrap with a shared sidebar/navbar
linking to all apps."**
→ `templates/base.html` is the shared base (Bootstrap 5, the AdminLTE/Bootstrap family) with a
sidebar + navbar; every page `{% extends "base.html" %}`.

**• "Use Django's app namespacing and `{% url %}` tags; do not hardcode links."**
→ Each app's `urls.py` sets `app_name = "…"`; templates navigate with `{% url 'dashboard:home' %}`,
`{% url 'data_api:readings' %}`, etc. No hardcoded paths.

**App responsibility mapping (brief → our project):**

| Brief's app | Our app | Responsibility | Key files |
|---|---|---|---|
| dashboard/core | `dashboard` | landing dashboard, base template, combined charts | `views.py`, `insights.py`, `templates/dashboard/home.html` |
| data_api (app 1) | `data_api` | connects to IQAir with token, fetches & stores on schedule | `services.py`, `scheduler.py`, `models.py` |
| predictor (app 2) | `predictor` | loads ML model, predicts from latest data, saves w/ timestamp | `services.py`, `models.py` |
| accounts/reports (app 3) | `reports` | login/logout + historical reports + CSV export | `views.py`, `urls.py`, `templates/reports/` |
| api (4th, DRF) | `api` | JSON endpoints consumed by charts + tested in Postman | `views.py`, `serializers.py`, `urls.py` |

**Logic.** Apps are registered in `config/settings.py` `INSTALLED_APPS`; `config/urls.py` includes each
app's `urls.py` with its namespace.

---

## 3.2 Dynamic External API Integration

**1. "Use the `requests` library to call the chosen external API."**
→ `data_api/services.py:48` — `resp = requests.get(url, params=params, timeout=timeout)`.

**2. "Use the API token/key to access the APIs."**
→ `data_api/services.py:41-46` passes the key as a param:
```python
params = {"city": city, "state": state, "country": country, "key": settings.AIRVISUAL_API_KEY}
```
The key is read from `.env` (`config/settings.py:161`), never hardcoded.

**3. "Verify the response code before processing; handle failures, timeouts, invalid tokens gracefully
with user-friendly messages."**
→ `data_api/services.py:47-60`:
```python
try:
    resp = requests.get(...)
except requests.exceptions.Timeout:
    raise IQAirError(f"Timeout contacting IQAir for {city}.")
except requests.exceptions.RequestException as exc:
    raise IQAirError(f"Network error … {exc}")
if resp.status_code != 200:
    raise IQAirError(f"IQAir returned HTTP {resp.status_code} …")
if payload.get("status") != "success":
    raise IQAirError("IQAir status != success …")
```
User-friendly messages: the **"Fetch now"** view (`data_api/views.py`) shows a Django `messages`
banner ("Fetched N reading(s); M error(s)"); failures never crash the app (`fetch_and_store_all`
collects errors and continues — `services.py:88-106`).

**4. "Implement a refresh mechanism so data updates at least every few seconds/minutes."**
→ APScheduler in `data_api/scheduler.py:67-78`:
```python
interval = max(1, settings.FETCH_INTERVAL_MINUTES)   # = 5 from .env
scheduler.add_job(_fetch_job, trigger=IntervalTrigger(minutes=interval),
                  id="fetch_air_quality", next_run_time=timezone.now())
```
Started automatically in `data_api/apps.py:11-25`.

**5. "Persist every fetched reading into a PostgreSQL table with a timestamp field
(DateTimeField, auto_now_add or explicit)."**
→ `data_api/models.py`: `fetched_at = models.DateTimeField(auto_now_add=True)` + `source_ts`.
Insert at `data_api/services.py:99` — `AirQualityReading.objects.create(**fields)`.

**Link.** `https://api.airvisual.com/v2/city?city=…&state=…&country=…&key=<TOKEN>`

---

## 3.3 MySQL/PostgreSQL Database

**• "settings.py configured with the MySQL/PostgreSQL endpoint."**
→ `config/settings.py:~88-104`:
```python
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": env("DB_NAME", "air_quality_db"),
    "USER": env("DB_USER"), "PASSWORD": env("DB_PASSWORD"),
    "HOST": env("DB_HOST", "127.0.0.1"), "PORT": env("DB_PORT", "5432"),
}}
```

**• "Proper Django models with migrations for raw API readings, prediction results, and (optionally)
user/group metadata."**
→ `data_api/models.py` → `AirQualityReading` (raw readings); `predictor/models.py` → `Prediction`
(results); Django's built-in `User` (auth). Migrations under each app's `migrations/`. Tables:
`data_api_airqualityreading`, `predictor_prediction`, `auth_user`.

**• "Each prediction record must store: input snapshot/reference, predicted value, model used, timestamp."**
→ `predictor/models.py` `Prediction` fields:
- `reading` (FK) + `input_features` (JSON snapshot) → **input reference/snapshot**
- `predicted_aqi_us`, `predicted_category` → **predicted value**
- `model_used` → **model used**
- `created_at` (auto_now_add) → **timestamp**

---

## 3.4 Machine Learning Model (Historical Data → Prediction)

**6. "Collect or download historical data for the chosen domain."**
→ Downloaded **12 months of hourly** AQI + weather for Kigali & Delhi, saved to
`ml/data/historical_air_quality.csv`.
Links:
- `https://air-quality-api.open-meteo.com/v1/air-quality` (hourly `us_aqi`, `pm2_5`)
- `https://archive-api.open-meteo.com/v1/archive` (hourly temperature, humidity, pressure, wind)

**7. "Clean and prepare the dataset; justify the choice of algorithm."**
→ In `ml/train_model.ipynb`: merge AQI + weather on the hourly timestamp, drop NaNs, engineer features
`[aqi_us, temperature_c, humidity, pressure_hpa, wind_speed_ms, hour, month]`, and create two targets
(AQI **+1h** and **+24h**). **Algorithm = Random Forest**, justified: handles non-linear
weather↔pollution interactions, needs no scaling, robust to outliers, exposes feature importances.

**8. "Train and evaluate the model offline using appropriate metrics (RMSE, MAE, accuracy, F1)."**
→ Trained in the notebook (offline). **Regression:** RMSE, MAE, R². **Classification:** accuracy, F1,
confusion matrix. Results: **+1h R² ≈ 0.997** (persistence), **+24h R² ≈ 0.83, acc ≈ 0.86** (real forecast).

**9. "Export the trained model using pickle or joblib."**
→ Exported with **joblib** to `ml/artifacts/`: `aqi_regressor_1h.joblib`, `aqi_classifier_1h.joblib`,
`aqi_regressor_24h.joblib`, `aqi_classifier_24h.joblib`.

**10. "Load the saved model inside the Django app and use the latest live API data to generate a fresh
prediction each time new data arrives."**
→ `predictor/services.py`: `load_models()` (lines 53-66) loads the 4 `.joblib` files;
`predict_from_reading()` (lines 93-146) builds features from the **latest reading** and predicts.
A **fresh prediction is generated on every scheduled fetch** — `data_api/scheduler.py:39-41`:
```python
for reading in summary["created"]:
    predict_from_reading(reading, save=True)
```

**11. "Display the prediction interactively on the dashboard and save the predicted value with date and
time into the database."**
→ Displayed on the dashboard: the AQI gauge card + the "our ML +24h" point on the trend chart
(`dashboard/templates/dashboard/home.html`). Saved with timestamp: each `Prediction` row has
`created_at` (`predictor/services.py:133-144`).

---

## 3.5 Dashboard, Charts

**• "Dashboard must show live current value(s), historical trend, and the ML prediction — all in one
view, plus links to each app's detail page."**
→ `dashboard/templates/dashboard/home.html` (single-page "command center") shows, per city: the live
**AQI gauge** (current value), the **AQI trend** chart (history), and the **ML +24h** prediction — all
together. The sidebar (`templates/base.html`) links to each app's page (Live Readings, Predictions,
Reports).

**• "At least two interactive charts (Chart.js) — e.g. a line chart of historical + predicted, and a
gauge/bar/pie for current status."**
→ We have **four** interactive visualizations: **line chart** (history + Open-Meteo forecast + our ML
prediction), **gauge** (current AQI), **bar chart** (pollutant breakdown) — all Chart.js — plus a
**Leaflet map**. ✅ exceeds the "≥2" requirement.

**• "Dashboard should auto-refresh or provide a refresh control."**
→ Both: JavaScript in `home.html` polls `/api/insights/` every 60s and `/api/stats/` every 15s and
redraws without reloading; there is also a manual **refresh button**.

---

## 3.6 DRF & Postman

**• "Expose at least three REST endpoints via DRF: (1) current/historical data, (2) predictions, (3)
feed new data and let the system make a prediction."**
→ `api/urls.py` + `api/views.py`:

| # | Method | Endpoint | View | Requirement met |
|---|---|---|---|---|
| 1 | GET | `/api/readings/` | `ReadingListAPIView` | current/historical data |
| 2 | GET | `/api/predictions/` | `PredictionListAPIView` | predictions |
| 3 | POST | `/api/predict/` | `PredictAPIView` | **feed data → prediction** |
| + | GET | `/api/insights/`, `/api/stats/` | `InsightsAPIView`, `stats` | extra (used by dashboard) |

**• "Use DRF serializers and viewsets/generic views appropriately."**
→ `api/serializers.py`: `AirQualityReadingSerializer`, `PredictionSerializer` (ModelSerializers).
`api/views.py`: `ListAPIView` (generic, for GET lists) + `APIView` (for the POST predict). `POST
/api/predict/` returns **201 Created** with a prediction per horizon.

**• "Provide a Postman collection (exported .json) demonstrating GET/POST with sample responses."**
→ `postman/AirQuality.postman_collection.json` (exported). Test steps in `POSTMAN_TESTING.md`. No token
needed (`AllowAny`).

**Logic.** Our dashboard consumes these same endpoints, so the API is real and used — not just built for
marks.

---

# 4. Marking Scheme — how we earn each component

| Component (marks) | How we satisfy it |
|---|---|
| **Django Project & App Architecture — MVT (6)** | 1 project + 5 apps, clean MVT, namespaced URLs, `.env`-driven settings (§3.1) |
| **Dynamic External API Integration (6)** | `requests` + token, `status_code==200` check + error handling, 5-min scheduler, timestamped inserts (§3.2) |
| **PostgreSQL Integration (5)** | `DATABASES` on PostgreSQL, migrated models, live data + predictions persisted with timestamps (§3.3) |
| **AdminLTE/Bootstrap Dashboard UI (4)** | Bootstrap-5 base template, responsive, sidebar/navbar linking all apps (§3.1/§3.5) |
| **Charts & Data Visualization (4)** | 4 live charts (gauge, pollutant bar, trend/forecast line, map), auto-refresh (§3.5) |
| **ML Model Training (4)** | Random Forest trained offline on 12-month history, metrics, joblib export, justified (§3.4 #6-9) |
| **ML Integration + Live Prediction (3)** | Models loaded in `predictor`, predict from live data each fetch, shown on dashboard (§3.4 #10-11) |
| **DRF API Layer & Postman (2)** | 3 core endpoints + serializers/views, exported Postman collection (§3.6) |
| **Code Quality, Documentation & Viva (2 + 4)** | README, requirements.txt, clean code, plus this doc set + `VIVA_PREP.md` (§Deliverables) |

---

**Deliverables:** source (zipped), `requirements.txt`, `README.md`, `ml/train_model.ipynb`,
`CONTRIBUTIONS.md` — all present. Supporting docs: `HOW_WE_BUILT_IT.md`, `PROJECT_WALKTHROUGH.md`,
`VIVA_PREP.md`, `POSTMAN_TESTING.md`.
