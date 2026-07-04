# Postman Testing Guide (Guideline 3.6)

The DRF endpoints are **open** (`AllowAny`) — no token or login is needed in Postman.

## 0. Start the server
```powershell
C:\Users\buble\aqenv\Scripts\Activate.ps1
python manage.py runserver
```
Base URL: `http://127.0.0.1:8000`

## 1. Import the collection (VSCode Postman extension)
1. Open the **Postman** panel in VSCode → **Collections** → **Import**.
2. Choose `postman/AirQuality.postman_collection.json` from this project.
3. The 4 requests appear under **Air Quality Dashboard API**. `{{base_url}}` is preset to `http://127.0.0.1:8000`.

## 2. The required endpoints (map to the rubric)

| # | Rubric requirement | Request | Expect |
|---|--------------------|---------|--------|
| 1 | current/historical data | `GET {{base_url}}/api/readings/` | 200, paginated JSON `{count, results:[...]}` |
| 2 | predictions | `GET {{base_url}}/api/predictions/` | 200, paginated JSON of predictions (both +1h & +24h) |
| 3 | feed new data → predict | `POST {{base_url}}/api/predict/` | 201, a fresh prediction per horizon |

Bonus: `GET {{base_url}}/api/insights/?city=Kigali&range=24h` — enriched bundle (pollutants, climate, forecast, advisory).

### POST /api/predict/ — request details
- Method: **POST**
- Header: `Content-Type: application/json`
- Body (raw / JSON):
```json
{ "city": "Kigali" }
```
- Or `{ "reading_id": 12 }` to predict from a specific reading, or `{}` for the latest reading overall.
- Response (201):
```json
[
  {"city":"Kigali","horizon_hours":1,"predicted_aqi_us":81.9,"predicted_category":"Moderate","model_used":"RandomForestRegressor, RandomForestClassifier", ...},
  {"city":"Kigali","horizon_hours":24,"predicted_aqi_us":80.2,"predicted_category":"Moderate", ...}
]
```
- If the model isn't trained yet you'll get **503** with a helpful message — run `ml/train_model.ipynb` first.

## 3. For the submission
- Send each request, then **Save Response** (or screenshot the request + response) — the rubric asks for the collection "with sample responses."
- The exported collection (`postman/AirQuality.postman_collection.json`) is already a deliverable; keep it in the zip.
