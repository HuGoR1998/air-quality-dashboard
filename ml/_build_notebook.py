"""Generate ml/train_model.ipynb from source cells using nbformat.

Run once:  python ml/_build_notebook.py
Then execute the notebook to train + export the models.
"""

from pathlib import Path

import nbformat as nbf

MD_TITLE = r'''# Air Quality Prediction — Model Training

Trains models on **hourly historical data for Kigali and Delhi** (free Open-Meteo archive)
at **two forecast horizons**, to contrast a trivial baseline with a real forecast:

- **+1 hour** — a *persistence* baseline (next-hour AQI ~= current AQI, very high R^2 but trivial)
- **+24 hours** — a genuine *next-day* forecast where weather, hour and season actually matter

For each horizon we train:

- **Regression** — the AQI value (`RandomForestRegressor`)
- **Classification** — the AQI category (`RandomForestClassifier`)

Feature set (matches the live IQAir data fed in by the Django `predictor` app):
`aqi_us, temperature_c, humidity, pressure_hpa, wind_speed_ms, hour, month`.

**Why Random Forest?** Handles non-linear weather/pollution interactions, needs no
scaling, is robust to outliers, and exposes feature importances. Trees are depth-limited
so the exported `.joblib` files stay small enough to submit.

Exports four artifacts to `ml/artifacts/`:
`aqi_regressor_1h`, `aqi_classifier_1h`, `aqi_regressor_24h`, `aqi_classifier_24h`.'''

C_IMPORTS = r'''import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import requests
import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    root_mean_squared_error, mean_absolute_error, r2_score,
    accuracy_score, f1_score, classification_report, confusion_matrix,
)

# Resolve project paths whether the notebook runs from the project root or ml/
BASE = Path.cwd()
if BASE.name == "ml":
    BASE = BASE.parent
DATA_DIR = BASE / "ml" / "data"
ART_DIR = BASE / "ml" / "artifacts"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ART_DIR.mkdir(parents=True, exist_ok=True)
print("Project base:", BASE)'''

MD_DOWNLOAD = r'''## 1. Download historical data (Open-Meteo)

12 months of hourly air quality (`us_aqi`, `pm2_5`) + weather
(`temperature, humidity, surface pressure, wind speed`) for each city.
Wind is requested in m/s so it matches IQAir's live units.'''

C_DOWNLOAD = r'''CITIES = {
    "Kigali": (-1.9499, 30.0588),
    "Delhi": (28.6667, 77.1167),
}
START, END = "2025-07-01", "2026-06-30"   # ~12 months of hourly data

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_city(name, lat, lon):
    aq = requests.get(AQ_URL, params={
        "latitude": lat, "longitude": lon,
        "hourly": "us_aqi,pm2_5",
        "start_date": START, "end_date": END, "timezone": "UTC",
    }, timeout=120).json()
    wx = requests.get(WX_URL, params={
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m",
        "start_date": START, "end_date": END, "timezone": "UTC",
        "wind_speed_unit": "ms",
    }, timeout=120).json()

    aq_df = pd.DataFrame(aq["hourly"]).rename(columns={"us_aqi": "aqi_us"})
    wx_df = pd.DataFrame(wx["hourly"]).rename(columns={
        "temperature_2m": "temperature_c",
        "relative_humidity_2m": "humidity",
        "surface_pressure": "pressure_hpa",
        "wind_speed_10m": "wind_speed_ms",
    })
    df = pd.merge(aq_df, wx_df, on="time")
    df["city"] = name
    return df


frames = [fetch_city(name, lat, lon) for name, (lat, lon) in CITIES.items()]
data = pd.concat(frames, ignore_index=True)
data["time"] = pd.to_datetime(data["time"])
data.to_csv(DATA_DIR / "historical_air_quality.csv", index=False)
print("Downloaded rows:", len(data))
data.head()'''

MD_FEATURES = r'''## 2. Feature engineering

Two forecast targets are created by shifting AQI within each city:
`target_aqi_1h` (shift -1) and `target_aqi_24h` (shift -24).
Categories follow the US EPA AQI bands.'''

C_FEATURES = r'''data = data.sort_values(["city", "time"]).reset_index(drop=True)
data["hour"] = data["time"].dt.hour
data["month"] = data["time"].dt.month

# Two forecast horizons
data["target_aqi_1h"] = data.groupby("city")["aqi_us"].shift(-1)
data["target_aqi_24h"] = data.groupby("city")["aqi_us"].shift(-24)

FEATURES = ["aqi_us", "temperature_c", "humidity", "pressure_hpa", "wind_speed_ms", "hour", "month"]


def aqi_category(aqi):
    bands = [(50, "Good"), (100, "Moderate"), (150, "Unhealthy for Sensitive Groups"),
             (200, "Unhealthy"), (300, "Very Unhealthy"), (10**9, "Hazardous")]
    for upper, label in bands:
        if aqi <= upper:
            return label
    return "Hazardous"


print("Total rows:", len(data))
print(data[["aqi_us", "temperature_c", "humidity", "pressure_hpa", "wind_speed_ms"]].describe().round(1))'''

MD_TRAIN = r'''## 3. Train both horizons (regression + classification)

Tree depth and leaf size are capped to keep the exported models small.'''

C_TRAIN = r'''HORIZONS = [1, 24]
RF_REG = dict(n_estimators=100, max_depth=14, min_samples_leaf=8, random_state=42, n_jobs=-1)
RF_CLS = dict(n_estimators=120, max_depth=16, min_samples_leaf=4, random_state=42, n_jobs=-1)

models = {}
results = {}

for h in HORIZONS:
    tgt = f"target_aqi_{h}h"
    sub = data.dropna(subset=FEATURES + [tgt]).reset_index(drop=True)
    X = sub[FEATURES].to_numpy()
    y_reg = sub[tgt].to_numpy()
    y_cls = sub[tgt].apply(aqi_category).to_numpy()

    # Regression
    Xtr, Xte, ytr, yte = train_test_split(X, y_reg, test_size=0.2, random_state=42)
    reg = RandomForestRegressor(**RF_REG).fit(Xtr, ytr)
    pr = reg.predict(Xte)
    rmse = root_mean_squared_error(yte, pr)
    mae = mean_absolute_error(yte, pr)
    r2 = r2_score(yte, pr)

    # Classification
    Xtr, Xte, ytr, yte = train_test_split(X, y_cls, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(**RF_CLS).fit(Xtr, ytr)
    pc = clf.predict(Xte)
    acc = accuracy_score(yte, pc)
    f1 = f1_score(yte, pc, average="weighted")

    models[h] = (reg, clf)
    results[h] = {"rows": len(sub), "rmse": rmse, "mae": mae, "r2": r2,
                  "acc": acc, "f1": f1,
                  "y_true": yte, "y_pred": pc, "labels": sorted(set(y_cls))}

    imp = pd.Series(reg.feature_importances_, index=FEATURES).sort_values(ascending=False)
    print(f"[+{h:>2}h] rows={len(sub):>6}  REG: RMSE={rmse:5.2f} MAE={mae:5.2f} R2={r2:.3f}"
          f"   CLS: acc={acc:.3f} f1={f1:.3f}")
    print("        top features: " + ", ".join(f"{f}={v:.3f}" for f, v in imp.head(3).items()))'''

MD_CONTRAST = r'''### Reading the contrast

- **+1h** leans almost entirely on `aqi_us` (persistence) — high R^2 but it is mostly
  echoing the current value.
- **+24h** spreads importance onto weather / `hour` / `month`, so the model is genuinely
  forecasting. Its R^2 is lower but far more meaningful — this is the model to defend in the viva.'''

MD_CLS_REPORT = r'''## 4. Per-class report + confusion matrix (+24h classifier)'''

C_CLS_REPORT = r'''h = 24
print(classification_report(results[h]["y_true"], results[h]["y_pred"]))

labels = results[h]["labels"]
cm = confusion_matrix(results[h]["y_true"], results[h]["y_pred"], labels=labels)
fig, ax = plt.subplots(figsize=(6, 5))
ax.imshow(cm, cmap="Blues")
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=45, ha="right")
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels)
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_title(f"Confusion Matrix (+{h}h)")
for i in range(len(labels)):
    for j in range(len(labels)):
        ax.text(j, i, cm[i, j], ha="center", va="center")
plt.tight_layout()
plt.show()'''

MD_EXPORT = r'''## 5. Export models (joblib)

Four artifacts saved into `ml/artifacts/`, then loaded by the Django `predictor` app.'''

C_EXPORT = r'''for h, (reg, clf) in models.items():
    joblib.dump(reg, ART_DIR / f"aqi_regressor_{h}h.joblib")
    joblib.dump(clf, ART_DIR / f"aqi_classifier_{h}h.joblib")

print("Saved artifacts:")
for p in sorted(ART_DIR.glob("*.joblib")):
    print(f" - {p.name:<28} {p.stat().st_size/1e6:6.2f} MB")'''

nb = nbf.v4.new_notebook()
nb.cells = [
    nbf.v4.new_markdown_cell(MD_TITLE),
    nbf.v4.new_code_cell(C_IMPORTS),
    nbf.v4.new_markdown_cell(MD_DOWNLOAD),
    nbf.v4.new_code_cell(C_DOWNLOAD),
    nbf.v4.new_markdown_cell(MD_FEATURES),
    nbf.v4.new_code_cell(C_FEATURES),
    nbf.v4.new_markdown_cell(MD_TRAIN),
    nbf.v4.new_code_cell(C_TRAIN),
    nbf.v4.new_markdown_cell(MD_CONTRAST),
    nbf.v4.new_markdown_cell(MD_CLS_REPORT),
    nbf.v4.new_code_cell(C_CLS_REPORT),
    nbf.v4.new_markdown_cell(MD_EXPORT),
    nbf.v4.new_code_cell(C_EXPORT),
]
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb.metadata["language_info"] = {"name": "python"}

out = Path(__file__).parent / "train_model.ipynb"
nbf.write(nb, str(out))
print("Notebook written:", out)
