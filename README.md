# Real-Time Environmental Health Monitoring & Air Quality Prediction Dashboard

> Web Technologies and API Services — Final Group Project (AUCA)
> A Django project that consumes the **IQAir AirVisual** live API, stores readings in
> **PostgreSQL**, forecasts air quality with **Machine Learning**, and presents everything
> in an **AdminLTE/Bootstrap** dashboard with interactive Chart.js charts.

---

## 1. Domain & API

- **Domain:** Air Quality (Environmental Health)
- **External API:** [IQAir AirVisual API](https://api-docs.iqair.com/) — token-based, near-real-time
- **Endpoint used:** `GET https://api.airvisual.com/v2/city?city={CITY}&state={STATE}&country={COUNTRY}&key={API_KEY}`
- **Cities monitored:** **Kigali** (Rwanda) and **Delhi** (India) — a clean-vs-polluted comparison that drives the dashboard charts. Configured via `AQ_LOCATIONS` in `.env`.
- **Returned fields we store:** US AQI, CN AQI, main pollutant, temperature, humidity, wind speed, pressure, source timestamp
- **Refresh:** an APScheduler job polls the API every `FETCH_INTERVAL_MINUTES` minutes; every poll is a live call saved with its own timestamp.

## 2. Architecture (Django apps)

| App | Responsibility |
|-----|----------------|
| `dashboard` | AdminLTE base template, landing dashboard, combined charts & navigation |
| `data_api`  | Calls IQAir with the API token, fetches & stores live readings on a schedule |
| `predictor` | Loads the trained ML model, predicts from the latest reading, logs predictions |
| `reports`   | User authentication + historical reports + CSV export of prediction log |
| `api`       | Django REST Framework JSON endpoints (readings, predictions, predict) |

## 3. Setup & Run

See **[SETUP.md](SETUP.md)** for the full step-by-step bootstrap. Quick version:

```powershell
# NOTE: venv lives at a short path (Windows long-path workaround) — see SETUP.md
python -m venv C:\Users\buble\aqenv
C:\Users\buble\aqenv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then edit .env with your real keys
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 4. Database connection notes (PostgreSQL)

- Create a database named `air_quality_db` and a user (see `.env`).
- Connection settings are read from `.env` by `config/settings.py`.
- Models: `AirQualityReading` (data_api), `Prediction` (predictor). Migrations under each app.

## 5. Machine Learning summary

- **Training data:** 12 months of **hourly** historical AQI + weather for Kigali & Delhi,
  downloaded from the free **Open-Meteo** archive (`ml/data/historical_air_quality.csv`).
  IQAir remains the live/token source; Open-Meteo is only the offline training source.
- **Two forecast horizons** (trained as both regression + classification):
  - **+1 hour** — a *persistence* baseline (RMSE ≈ 6, R² ≈ 0.997, but essentially echoes current AQI).
  - **+24 hours** — a genuine *next-day* forecast (RMSE ≈ 46, R² ≈ 0.83; acc ≈ 0.86, F1 ≈ 0.85)
    where weather/pressure/wind actually contribute. **This is the model to defend in the viva.**
- **Algorithm:** RandomForest (regressor + classifier) — non-linear, no scaling, exposes
  feature importances; depth-limited so the `.joblib` files stay small.
- **Training:** offline in `ml/train_model.ipynb`; exports four artifacts to `ml/artifacts/`:
  `aqi_regressor_1h`, `aqi_classifier_1h`, `aqi_regressor_24h`, `aqi_classifier_24h`.
- **Inference:** the `predictor` app loads all four models and feeds the latest live IQAir
  reading in; the scheduler logs a prediction per horizon with a timestamp on every fetch.

## 6. DRF endpoints (tested in Postman — see `postman/`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET  | `/api/readings/`    | current + historical readings |
| GET  | `/api/predictions/` | prediction history |
| POST | `/api/predict/`     | feed a current reading → returns a prediction |

## 7. Team & contributions

See **[CONTRIBUTIONS.md](CONTRIBUTIONS.md)** (Deliverable #16).
