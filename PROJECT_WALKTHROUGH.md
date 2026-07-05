# Project Walkthrough — Detailed, Code-Referenced (Start to Finish)

Real-Time Environmental Health Monitoring & Air Quality Prediction Dashboard
Domain: **Air Quality** · Live API: **IQAir AirVisual** · DB: **PostgreSQL** · ML: **Random Forest**

> Every claim below points to the exact **file** and **line** so anyone can open it and see it
> (great for the viva: *"show me where X happens"*).

---

## 0. One-sentence summary
A Django app **fetches live air-quality data from IQAir every 5 minutes**, **stores it in
PostgreSQL**, **forecasts future AQI with a trained ML model**, and **shows everything on a
live dashboard**, exposing the data through a **REST API tested in Postman**.

### The whole data flow at a glance
```
                    ┌──────────────── OPEN-METEO (free, no key) ─────────────────┐
                    │ (a) 12-month hourly history → ML training (ml/train_model)  │
                    │ (b) live enrichment → dashboard/insights.py                 │
                    └────────────────────────────────────────────────────────────┘
                                             │
 IQAir API ─(5 min, token)→ data_api ──► PostgreSQL ──► predictor ──► PostgreSQL ──► DRF API ──► Dashboard
 (live AQI+weather)         fetch+save    readings      ML (.joblib)   predictions    /api/...    browser JS
```

---

## 1. The nature of our data

**Two sources, two jobs:**

| Source | Auth | Role | Fields we use |
|---|---|---|---|
| **IQAir AirVisual** | API key (token) ✅ | **Live** source | US/CN AQI, main pollutant, temp, humidity, pressure, wind, timestamp — per city |
| **Open-Meteo** | none | **Training history** + **display enrichment** | 12-month hourly AQI+weather (ML); pollutant breakdown, UV, cloud, forecast (dashboard) |

**The exact IQAir → database field mapping** lives in `data_api/services.py:65-85`
(`parse_reading()`): e.g. IQAir's `pollution.aqius → aqi_us`, `weather.tp → temperature_c`,
`weather.ws → wind_speed_ms`, `pollution.ts → source_ts`.

**Cities:** Kigali (clean-ish) + Delhi (polluted) — defined in `.env` as `AQ_LOCATIONS`
and parsed in `config/settings.py:166-196`.

**Why "hourly" is fine:** AQI is an hourly measure at the source. The assignment's
*"every few minutes"* rule is about **our polling cadence**, not the source — see §4.

---

## 2. Requirements → where each mark is earned

| Rubric line (marks) | File(s) |
|---|---|
| Architecture — MVT (6) | `config/` + apps `dashboard`, `data_api`, `predictor`, `reports`, `api` |
| External API integration (6) | `data_api/services.py`, `data_api/scheduler.py` |
| PostgreSQL (5) | `config/settings.py` (DATABASES) + models + migrations |
| Dashboard UI (4) | `templates/base.html`, `dashboard/templates/dashboard/home.html` |
| Charts & viz (4) | `dashboard/templates/dashboard/home.html` (Chart.js + Leaflet) |
| ML training (4) | `ml/train_model.ipynb` |
| ML integration (3) | `predictor/services.py` |
| DRF & Postman (2) | `api/`, `postman/AirQuality.postman_collection.json` |
| Docs & viva (2+4) | `README.md`, `PROJECT_WALKTHROUGH.md`, `VIVA_PREP.md` |

---

## 3. Database & connection

**Credentials** come from `.env` and are read in `config/settings.py` (~lines 90-104):
```python
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": env("DB_NAME", "air_quality_db"),
    "USER": env("DB_USER", "postgres"),
    "PASSWORD": env("DB_PASSWORD", ""),
    "HOST": env("DB_HOST", "127.0.0.1"),
    "PORT": env("DB_PORT", "5432"),
}}
```
`env()` is a small helper (top of `settings.py`) that reads from `.env` via `python-dotenv`
(`load_dotenv(BASE_DIR / ".env")`).

**Models → tables** (created by `makemigrations` + `migrate`):
- `data_api/models.py` → table **`data_api_airqualityreading`**
- `predictor/models.py` → table **`predictor_prediction`**

**Every fetch = one `INSERT`** — see `data_api/services.py:99`
(`AirQualityReading.objects.create(**fields)`). That's why the row count keeps climbing.

---

## 4. ★ The 5-minute fetch — traced through the actual code

This is the exact chain, hop by hop:

**① The interval value** — `.env`:
```
FETCH_INTERVAL_MINUTES=5
```
read in `config/settings.py:163`:
```python
FETCH_INTERVAL_MINUTES = int(env("FETCH_INTERVAL_MINUTES", "5"))
```

**② The scheduler starts** when the server boots — `data_api/apps.py:11-25`
(`DataApiConfig.ready()`), which only runs under `runserver` and calls `scheduler.start()`:
```python
def ready(self):
    if "runserver" not in sys.argv:
        return
    ...
    from data_api import scheduler
    scheduler.start()
```

**③ The 5-minute job is registered** — `data_api/scheduler.py:61-78` (`start()`):
```python
interval = max(1, settings.FETCH_INTERVAL_MINUTES)          # line 67  → 5
scheduler = BackgroundScheduler(timezone=str(settings.TIME_ZONE))
scheduler.add_jobstore(DjangoJobStore(), "default")
scheduler.add_job(
    _fetch_job,
    trigger=IntervalTrigger(minutes=interval),               # line 73  → every 5 min
    id="fetch_air_quality",                                  # line 74
    max_instances=1,
    replace_existing=True,
    next_run_time=timezone.now(),                            # line 77  → also fetch immediately
)
```
So **`IntervalTrigger(minutes=5)` on line 73 of `data_api/scheduler.py` is literally "the 5-minute fetch."**

**④ What the job does each tick** — `data_api/scheduler.py:24-52` (`_fetch_job()`):
```python
summary = fetch_and_store_all()                # fetch + save all cities
for reading in summary["created"]:
    predict_from_reading(reading, save=True)   # then predict on each new reading
```

**⑤ The actual IQAir call** — `data_api/services.py:35-62` (`fetch_city()`): builds the URL
with the token, calls `requests.get(...)`, and **verifies the response** (line 55):
```python
if resp.status_code != 200:
    raise IQAirError(...)                       # Guideline 3.2.3
```

**⑥ Save to PostgreSQL** — `data_api/services.py:88-106` (`fetch_and_store_all()`):
loops `settings.AQ_LOCATIONS`, calls `fetch_city()`, parses, and **inserts** (line 99):
```python
reading = AirQualityReading.objects.create(**fields)
```

**Manual trigger:** the same `fetch_and_store_all()` is called by the **"Fetch now"** button
(`data_api/views.py` → `fetch_now`) and by the management command
`python manage.py fetch_air_quality` (`data_api/management/commands/fetch_air_quality.py`).

**Job runs are logged** in the DB (`django_apscheduler_djangojobexecution`) — proof the
scheduler is alive.

---

## 5. The Machine Learning part

### Offline (training) — `ml/train_model.ipynb`
1. Download 12 months hourly AQI+weather for both cities (Open-Meteo).
2. Features = `[aqi_us, temperature_c, humidity, pressure_hpa, wind_speed_ms, hour, month]`;
   targets = AQI **+1h** and **+24h** (shifted per city).
3. Train **RandomForestRegressor** (the number) + **RandomForestClassifier** (the band) for each horizon.
4. Evaluate: **+1h** R² ≈ 0.997 (persistence, trivial) vs **+24h** R² ≈ 0.83 (real forecast).
5. Export 4 files → `ml/artifacts/aqi_{regressor,classifier}_{1h,24h}.joblib`.

### Online (inference) — `predictor/services.py`
- **The feature contract** (must match the notebook) — lines 28-36 (`FEATURE_COLUMNS`).
- **Loading the models** — lines 53-66 (`load_models()`): reads the 4 `.joblib` files from
  `ARTIFACT_DIR` (line 24 = `settings.BASE_DIR / "ml" / "artifacts"`), cached after first load.
- **Making a prediction** — lines 93-146 (`predict_from_reading()`): builds features from the
  live reading (lines 74-85), runs both models per horizon, and saves a `Prediction` row
  (lines 133-144). Raises `ModelNotTrained` gracefully if the `.joblib` files are missing (line 100).

**Why Random Forest?** Non-linear, no scaling, robust, gives feature importances; depth-limited
so the files stay small.

---

## 6. Frontend & dashboard

- **Base layout** — `templates/base.html`: Bootstrap 5 sidebar + navbar + **theme toggle**
  (`data-bs-theme`, remembered in `localStorage`) + logout (POST form).
- **Command center** — `dashboard/templates/dashboard/home.html`: all panels + the JavaScript
  that polls the API and renders everything:
  - `loadAll()` fetches `/api/insights/?city=…` for each city (every 60s),
  - `pollStats()` fetches `/api/stats/` for the live counter (every 15s),
  - render functions draw the **gauge, pollutant bar, trend/forecast line** (Chart.js) and the
    **Leaflet map** with AQI-coloured markers.
- **View** — `dashboard/views.py` (`home`) just passes the city list + coordinates; all live
  data is loaded client-side.
- **Enrichment API data** — `dashboard/insights.py` (`get_enrichment`, `health_advisory`) calls
  Open-Meteo for pollutants/climate/forecast/history and is served by `api/views.py`
  (`InsightsAPIView`).
- **Auth + CSV** — `reports/views.py`: `reports`, `export_predictions_csv`, `export_readings_csv`;
  login/logout wired in `reports/urls.py`.

---

## 7. The REST API + Postman

**Endpoints** (`api/urls.py` → `api/views.py`):

| Method | Endpoint | View | Purpose |
|---|---|---|---|
| GET | `/api/readings/` | `ReadingListAPIView` | current + historical readings |
| GET | `/api/predictions/` | `PredictionListAPIView` | prediction history |
| POST | `/api/predict/` | `PredictAPIView` | feed a reading → returns a prediction |
| GET | `/api/insights/?city=` | `InsightsAPIView` | pollutants, climate, forecast, advisory |
| GET | `/api/stats/` | `stats` | live totals for the counter |

Serializers are in `api/serializers.py`. The API uses DRF `AllowAny`, so Postman needs no token.

**Postman steps (Guideline 3.6):**
1. `python manage.py runserver`.
2. **Import** `postman/AirQuality.postman_collection.json` (Ctrl+O).
3. Send `GET /api/readings/`, `GET /api/predictions/`, and `POST /api/predict/`
   (Body → raw → JSON → `{ "city": "Kigali" }`) → expect **201** with a prediction per horizon.
4. **Screenshot each request + response** (rubric wants sample responses).

Full guide: `POSTMAN_TESTING.md`.

---

## 8. Run it fresh
```powershell
C:\Users\buble\aqenv\Scripts\Activate.ps1     # activate the venv (short path)
python manage.py runserver                    # from the folder with manage.py
# open http://127.0.0.1:8000  →  log in  →  demo
```
PostgreSQL must be running (Windows service, auto-start).

---

## 9. "Show me where X happens" — viva quick-reference

| Examiner asks… | Open this |
|---|---|
| "Where's the 5-minute fetch?" | `data_api/scheduler.py:73` (`IntervalTrigger(minutes=interval)`) + `:67` (interval from settings) |
| "Where do you call the API with the token?" | `data_api/services.py:35-62` (`fetch_city`) |
| "Where do you verify the response?" | `data_api/services.py:55` (`status_code != 200`) |
| "Where is data saved to PostgreSQL?" | `data_api/services.py:99` (`AirQualityReading.objects.create`) |
| "Where does the DB connection get configured?" | `config/settings.py` DATABASES (~90-104) |
| "Where is the ML model loaded?" | `predictor/services.py:53-66` (`load_models`) |
| "Where is a prediction made & saved?" | `predictor/services.py:93-146` (`predict_from_reading`) |
| "Where are the DRF endpoints?" | `api/urls.py` + `api/views.py` |
| "Where do the charts get their data?" | `dashboard/templates/dashboard/home.html` (`loadAll` → `/api/insights/`) |

---

## 10. Where everything lives
```
config/            Django project (settings incl. DB + FETCH_INTERVAL_MINUTES + AQ_LOCATIONS)
data_api/          services.py (IQAir), scheduler.py (5-min job), models.py (readings), views.py
predictor/         services.py (load models + predict), models.py (predictions)
dashboard/         views.py, insights.py (Open-Meteo), templates/dashboard/home.html
reports/           views.py (auth + CSV), urls.py (login/logout)
api/               views.py, serializers.py, urls.py (the REST layer)
ml/                train_model.ipynb, data/, artifacts/*.joblib
templates/         base.html
static/            css/app.css + vendored Bootstrap/Leaflet/Chart.js/Font Awesome
postman/           AirQuality.postman_collection.json
```
