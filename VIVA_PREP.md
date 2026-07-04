# Viva Preparation

**How it works (Section 6):** live demo of the running system, then each member is asked
**1–2 questions about a part they did NOT build**. Worth **4 marks (Q/A)** + 2 for docs.
So everyone must understand the *whole* system, not just their slice.

---

## 1. Live demo script (do this in order)

1. `python manage.py runserver` → open `http://127.0.0.1:8000` → **log in** (shows auth).
2. **Dashboard:** point out the live counter ("N readings · last fetch Xs ago") — proves live data.
3. Click **Fetch now** on *Live Readings* → new rows appear → open **pgAdmin** → `SELECT count(*)` grows → proves **live fetch → PostgreSQL** (Guideline 3.2/3.3).
4. Show the **gauge, map, pollutant breakdown, climate panel, health advisory**.
5. Show the **trend + forecast chart**: history · Open-Meteo forecast · **our ML +24h** point.
6. Switch **Kigali ↔ Delhi**, change **range**, toggle **dark mode**.
7. **Postman:** send `GET /api/readings/`, `GET /api/predictions/`, `POST /api/predict/` → live prediction.
8. Show `ml/train_model.ipynb` metrics + the exported `.joblib` files.

---

## 2. Core Q&A (everyone should know these)

**Q: What API do you use and why is it valid?**
IQAir AirVisual — it requires an **API key/token**, returns **near-real-time** AQI, and has enough history (via Open-Meteo) to train on. Meets all three requirements in Section 2.

**Q: Your data is hourly — how is it "every few minutes"?**
The **requirement is about our refresh mechanism**, not the source. Our scheduler **polls IQAir every 5 minutes**; each poll is a live API call saved with its own `fetched_at`. AQI is inherently an hourly measure — no AQI API updates faster — so within an hour several polls may store the same value with different timestamps.

**Q: Where does the data live?**
**PostgreSQL** (`air_quality_db`). `data_api_airqualityreading` = raw readings; `predictor_prediction` = predictions. Both have timestamps.

**Q: How does the ML work end-to-end?**
Trained **offline** in a Jupyter notebook on 12 months of hourly data → exported with **joblib** → loaded in the `predictor` app → fed the **latest live reading** → produces a prediction that's shown on the dashboard and **logged with a timestamp**.

**Q: Why two forecast horizons?** *(strongest talking point)*
- **+1h** is a *persistence baseline* — next-hour AQI ≈ current AQI, so R² ≈ 0.997 but it's trivial (feature importance is ~all `aqi_us`).
- **+24h** is a *real forecast* — R² ≈ 0.83, and **weather/pressure/wind actually contribute**. This is the model that genuinely learns.

**Q: Why Random Forest?**
Handles non-linear weather↔pollution relationships, no feature scaling needed, robust to outliers, and gives **feature importances**. Trees are depth-limited so the `.joblib` files stay small.

**Q: Two data sources — why?**
**IQAir** = the live/token source (satisfies the token rule) + our stored readings & ML.
**Open-Meteo** = free/keyless **enrichment** (pollutant breakdown, climate, forecast, 12-month training history). Kept separate and clearly labelled.

**Q: What are the DRF endpoints?**
`GET /api/readings/` (current+historical), `GET /api/predictions/`, `POST /api/predict/` (feed data → prediction), plus `/api/insights/` and `/api/stats/`. Built with DRF serializers + views; tested in Postman.

**Q: How is the dashboard live?**
JavaScript polls the API on a timer (`/api/insights/` every 60s, `/api/stats/` every 15s) and re-renders the charts — no page reload.

---

## 3. Per-member prep

### Shema — you built Data/Backend, so expect questions on **ML or the frontend**
- *"How was the ML model trained and loaded into Django?"* → notebook → joblib → `predictor/services.py` loads it, feeds live features.
- *"How do the charts update without reloading?"* → JS polls the DRF endpoints on a timer.
- **Own area (be fluent):** MVT structure, IQAir token flow + error handling, the scheduler, PostgreSQL models/migrations.

### Thierry — you built ML, so expect questions on **the API integration or database**
- *"How does the app fetch live data and store it?"* → `data_api/services.py` calls IQAir with the token, checks status 200, saves an `AirQualityReading` row; the scheduler does it every 5 min.
- *"What DRF endpoints exist?"* → readings / predictions / predict.
- **Own area (be fluent):** feature engineering, +1h vs +24h, metrics (RMSE/MAE/R², accuracy/F1), why Random Forest, joblib export/load.

### Patrick — you built Frontend/API, so expect questions on **ML or the database**
- *"Why is the +24h model better than +1h even with lower R²?"* → persistence vs real forecast (see above).
- *"What tables are in PostgreSQL and what's in them?"* → readings + predictions, with timestamps.
- **Own area (be fluent):** Bootstrap 5 layout, Chart.js configs, Leaflet map, DRF serializers/views, Postman, auth + CSV export.

---

## 4. Likely "gotcha" questions + answers
- *"Is this real or mock data?"* → Real — press **Fetch now** live and watch the DB row count rise.
- *"What happens if the API is down?"* → `fetch_city()` catches timeouts/non-200/invalid-token and logs an error without crashing; the scheduler continues.
- *"Why does Delhi show higher AQI than Kigali?"* → Delhi is a heavily polluted megacity; we intentionally chose one clean-ish and one polluted city for contrast.
- *"Show me where the prediction is saved."* → `predictor_prediction` table / Predictions page — each row has city, horizon, predicted AQI, category, model, timestamp.
