# Group Contribution 

**Project:** Real-Time Environmental Health Monitoring & Air Quality Prediction Dashboard
**Domain / API:** Air Quality — IQAir AirVisual (live/token) + Open-Meteo (historical & enrichment)
**Course:** Web Technologies and API Services — Final Exam (AUCA, Gishushu)
**Team (3):** Shema Hugor · Thierry Sebakunzi  · Patrick Niyonshuti

---

## Member 1 — **Shema Hugor** ( Data & Backend)

- Set up the Django project (`config/`) and the **5-app MVT architecture** (`dashboard`, `data_api`, `predictor`, `reports`, `api`); settings, URL routing, `.env` secrets handling.
- Built the **IQAir AirVisual integration** in `data_api/services.py` — token auth, `requests`, status-code / timeout / error handling.
- Designed the **`AirQualityReading` model** + migrations; connected Django to **PostgreSQL**.
- Implemented the **APScheduler background job** (`data_api/scheduler.py`) — fetches live data every 5 minutes and logs each reading with a timestamp.
- Project coordination, `README.md`, `requirements.txt`, run/setup docs.

## Member 2 — **Thierry** (Machine Learning)

- Collected **historical training data** (12 months, hourly, Kigali + Delhi) from the Open-Meteo archive.
- Built `ml/train_model.ipynb`: feature engineering, trained **RandomForest regression + classification** at **two horizons (+1h persistence, +24h forecast)**, evaluated (RMSE/MAE/R², accuracy/F1), exported with `joblib`.
- Wrote the **`predictor` app** (`predictor/services.py`) — loads the models, builds features from live readings, generates a prediction per horizon, logs to the DB with timestamp.
- Built the **Open-Meteo enrichment** service (`dashboard/insights.py`) — pollutants, climate, forecast, history, health advisory.

## Member 3 — **Patrick** (Frontend & API Layer)

- Built the **dashboard UI** — single-page "command center" (Bootstrap 5), responsive layout, sidebar/navbar, **light/dark theme toggle**.
- Implemented **interactive visualizations** — Chart.js (AQI gauge, pollutant breakdown, trend + forecast), **Leaflet map** with AQI-colored markers, live counter + auto-refresh.
- Built the **DRF API layer** (`api/`) — serializers + views for `/readings/`, `/predictions/`, `/predict/`, `/insights/`, `/stats/`; exported the **Postman collection**.
- Built the **`reports` app** — user authentication (login/logout) and **CSV export** of readings & predictions.

---

