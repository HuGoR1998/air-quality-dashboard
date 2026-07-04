# ML — offline training (Deliverable #15)

```
ml/
├── train_model.ipynb          # trains + evaluates + exports (executed, with outputs)
├── _build_notebook.py         # regenerates the notebook from source cells (nbformat)
├── data/
│   └── historical_air_quality.csv   # 12 months hourly, Kigali + Delhi (Open-Meteo)
└── artifacts/
    ├── aqi_regressor_1h.joblib      # +1h  next-hour AQI (persistence baseline)
    ├── aqi_classifier_1h.joblib     # +1h  category
    ├── aqi_regressor_24h.joblib     # +24h next-day AQI (real forecast)
    └── aqi_classifier_24h.joblib    # +24h category
```

- **Source of historical data:** Open-Meteo air-quality + weather archive (free, no key),
  by coordinates, hourly. IQAir stays the live/token source for the running app.
- **Two horizons:** +1h (persistence, R² ≈ 0.997) vs +24h (real forecast, R² ≈ 0.83).
- **Regression:** RandomForestRegressor → RMSE, MAE, R².
- **Classification:** RandomForestClassifier → accuracy, F1, confusion matrix.
- Features (must match `predictor.services.FEATURE_COLUMNS`):
  `aqi_us, temperature_c, humidity, pressure_hpa, wind_speed_ms, hour, month`.

**Rebuild + run:** `python ml/_build_notebook.py` then execute `train_model.ipynb`
(or `jupyter nbconvert --to notebook --execute --inplace ml/train_model.ipynb`).
