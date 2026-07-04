# Group Contribution Sheet (Deliverable #16)

**Project:** Real-Time Environmental Health Monitoring & Air Quality Prediction Dashboard
**Domain / API:** Air Quality — IQAir AirVisual (live/token) + Open-Meteo (historical & enrichment)
**Course:** Web Technologies and API Services — Final Exam (AUCA, Gishushu)
**Team (3):** Shema Hugor · Thierry · Patrick

---

## Member 1 — **Shema Hugor** (Team Lead · Data & Backend)
**Rubric areas:** Django Project & Architecture (6) · API Integration (6) · Database (5)

- Set up the Django project (`config/`) and the **5-app MVT architecture** (`dashboard`, `data_api`, `predictor`, `reports`, `api`); settings, URL routing, `.env` secrets handling.
- Built the **IQAir AirVisual integration** in `data_api/services.py` — token auth, `requests`, status-code / timeout / error handling.
- Designed the **`AirQualityReading` model** + migrations; connected Django to **PostgreSQL**.
- Implemented the **APScheduler background job** (`data_api/scheduler.py`) — fetches live data every 5 minutes and logs each reading with a timestamp.
- Project coordination, `README.md`, `requirements.txt`, run/setup docs.

## Member 2 — **Thierry** (Machine Learning)
**Rubric areas:** ML Model Training (4) · ML Integration + Live Prediction (3)

- Collected **historical training data** (12 months, hourly, Kigali + Delhi) from the Open-Meteo archive.
- Built `ml/train_model.ipynb`: feature engineering, trained **RandomForest regression + classification** at **two horizons (+1h persistence, +24h forecast)**, evaluated (RMSE/MAE/R², accuracy/F1), exported with `joblib`.
- Wrote the **`predictor` app** (`predictor/services.py`) — loads the models, builds features from live readings, generates a prediction per horizon, logs to the DB with timestamp.
- Built the **Open-Meteo enrichment** service (`dashboard/insights.py`) — pollutants, climate, forecast, history, health advisory.

## Member 3 — **Patrick** (Frontend & API Layer)
**Rubric areas:** AdminLTE/Bootstrap Dashboard (4) · Charts & Visualization (4) · DRF & Postman (2)

- Built the **dashboard UI** — single-page "command center" (Bootstrap 5), responsive layout, sidebar/navbar, **light/dark theme toggle**.
- Implemented **interactive visualizations** — Chart.js (AQI gauge, pollutant breakdown, trend + forecast), **Leaflet map** with AQI-colored markers, live counter + auto-refresh.
- Built the **DRF API layer** (`api/`) — serializers + views for `/readings/`, `/predictions/`, `/predict/`, `/insights/`, `/stats/`; exported the **Postman collection**.
- Built the **`reports` app** — user authentication (login/logout) and **CSV export** of readings & predictions.

---

### Shared work & viva readiness
- Documentation, testing, and the live demo were prepared together.
- **Every member has reviewed the others' code** and can answer questions about the full system (per Evaluation, Section 6). See `VIVA_PREP.md`.
- All core logic (views, models, API handling, ML integration) is original group work; only the vendored Bootstrap/Leaflet/Chart.js/Font Awesome libraries are third-party (clearly attributed).
