# Viva Preparation

**How it works:** live demo of the running system, then each member is asked **1–2 questions about
a part they did NOT build**. So everyone must understand the *whole* system, not just their slice.

---

## 1. Live demo script (do this in order)
1. `python manage.py runserver` → open `http://127.0.0.1:8000` → **log in** (shows auth).
2. **Dashboard:** point out the live counter ("N readings · last fetch Xs ago") — proves live data.
3. Click **Fetch now** on *Live Readings* → new rows appear → open **pgAdmin** → `SELECT count(*)` grows → proves live fetch → PostgreSQL.
4. Show the **gauge, map, pollutant breakdown, climate panel, health advisory**.
5. Show the **trend + forecast chart**: history · Open-Meteo forecast · **our ML +24h**.
6. Switch **Kigali ↔ Delhi**, change **range**, toggle **dark mode**.
7. **Postman:** send `GET /api/readings/`, `GET /api/predictions/`, `POST /api/predict/` → live prediction.
8. Show `ml/train_model.ipynb` metrics + the exported `.joblib` files.

## 2. Core Q&A (everyone should know these)

**Q: What API do you use and why is it valid?** IQAir AirVisual — it requires a **token**, returns
**near-real-time** AQI, and has enough history (via Open-Meteo) to train on.

**Q: Your data is hourly — how is it "every few minutes"?** The requirement is about our **refresh
mechanism**: the scheduler **polls IQAir every 5 minutes**; each poll is a live call saved with its
own `fetched_at`. AQI itself is an hourly measure — no AQI API updates faster.

**Q: Where does the data live?** PostgreSQL. `data_api_airqualityreading` = readings;
`predictor_prediction` = predictions. Both timestamped.

**Q: How does the ML work end-to-end?** Trained **offline** in a notebook on 12 months of hourly data
→ exported with **joblib** → loaded in `predictor` → fed the latest live reading → prediction shown
on the dashboard and **logged with a timestamp**.

**Q: Why two forecast horizons?** +1h is a *persistence baseline* (R² ≈ 0.997 but trivial). +24h is a
*real forecast* (R² ≈ 0.87) where weather + trend features matter — the model to defend.

**Q: Why Random Forest?** Non-linear, no scaling, robust to outliers, gives feature importances.

**Q: Two data sources — why?** IQAir = the token-based live source + our ML input. Open-Meteo = free
enrichment (pollutants, climate, forecast) + the 12-month training history.

**Q: What are the DRF endpoints?** `GET /api/readings/`, `GET /api/predictions/`,
`POST /api/predict/` (feed data → prediction), plus `/api/insights/` and `/api/stats/`.

**Q: How is the dashboard live?** JavaScript polls the API on a timer (`/api/insights/` every 60s,
`/api/stats/` every 15s) and re-renders the charts — no page reload.

## 3. Per-role prep (the examiner asks about parts you did NOT build)

### If you built Data/Back-end → expect questions on ML or the front-end
- *"How was the ML model trained and loaded?"* → notebook → joblib → `predictor/services.py` loads it.
- *"How do the charts update without reloading?"* → JS polls the DRF endpoints on a timer.
- **Be fluent on:** MVT structure, IQAir token flow + error handling, the scheduler, PostgreSQL models.

### If you built ML → expect questions on the API integration or database
- *"How does the app fetch and store live data?"* → `data_api/services.py` calls IQAir, checks 200, saves a row; scheduler every 5 min.
- *"What DRF endpoints exist?"* → readings / predictions / predict.
- **Be fluent on:** feature engineering, +1h vs +24h, city + lag/trend features, metrics, joblib.

### If you built Front-end/API → expect questions on ML or the database
- *"Why is the +24h model better even with lower R²?"* → persistence vs real forecast.
- *"What tables are in PostgreSQL?"* → readings + predictions, timestamped.
- **Be fluent on:** Bootstrap 5 layout, Chart.js, Leaflet, DRF serializers/views, Postman, auth + CSV.

## 4. Likely "gotcha" questions + answers
- *"Is this real or mock data?"* → press **Fetch now** live and watch the DB count rise.
- *"What if the API is down?"* → `fetch_city()` catches timeouts/non-200/invalid-token and logs, without crashing.
- *"Why does Delhi show higher AQI than Kigali?"* → Delhi is a heavily polluted megacity; we chose one clean-ish and one polluted city for contrast.
- *"Why was Kigali's prediction off?"* → the model over-predicted a city mid-decline; we added lag/trend features so it now follows the direction (R² 0.83 → 0.87).
- *"Show me where the prediction is saved."* → `predictor_prediction` table / Predictions page.
