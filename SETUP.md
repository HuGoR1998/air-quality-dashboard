# SETUP — Bootstrap sequence (Windows / PowerShell)

Run these once, in order, from the project root. This scaffolds the exact app
structure the assignment requires (Guideline 3.1).

## 0. Prerequisites
- Python 3.11+  (`python --version`)
- PostgreSQL installed and running (`psql --version`)

## 1. Virtual environment + dependencies

> ⚠️ **Windows long-path note:** this project sits at a very deep folder path
> (OneDrive + long course folders). The PostgreSQL driver `psycopg2` fails to load
> its DLLs when the venv lives *inside* that deep path (`DLL load failed ... filename
> or extension is too long`). Fix: create the venv at a **short path outside** the
> project. We use `C:\Users\buble\aqenv`. (Also enable Windows long paths once, as
> admin: set `HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1`.)

```powershell
python -m venv C:\Users\buble\aqenv
C:\Users\buble\aqenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

From here on, "python" means `C:\Users\buble\aqenv\Scripts\python.exe`
(or just activate the venv first, as above).

## 2. Environment file
```powershell
Copy-Item .env.example .env
# Edit .env: set AIRVISUAL_API_KEY, DB_PASSWORD, and a new SECRET_KEY.
```

## 3. Create the PostgreSQL database
```powershell
psql -U postgres -c "CREATE DATABASE air_quality_db;"
```

## 4. Scaffold the Django project + 5 apps
```powershell
django-admin startproject config .
python manage.py startapp dashboard
python manage.py startapp data_api
python manage.py startapp predictor
python manage.py startapp reports
python manage.py startapp api
```

## 5. Wire up settings (done in code, next phase)
- Add the 5 apps + `rest_framework` + `django_apscheduler` to `INSTALLED_APPS`.
- Point `DATABASES` at PostgreSQL via `.env` (using `python-dotenv`).
- Configure `TEMPLATES`, `STATIC`, and the AdminLTE base template.

## 6. Migrate + first run
```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 7. Machine Learning (offline, once)
```powershell
jupyter notebook ml/train_model.ipynb
# Trains regression + classification models, exports to ml/artifacts/*.joblib
```

---
### Progress checklist (map to Marking Scheme, Section 4)
- [x] Django project + 5 apps, MVT separation ....... (6)
- [x] IQAir live fetch w/ token + error handling ..... (6)
- [x] PostgreSQL models + migrations + timestamps .... (5)
- [x] AdminLTE dashboard + navigation ................ (4)
- [x] 2+ interactive Chart.js charts ................. (4)
- [x] ML models trained offline + saved .............. (4)
- [x] ML loaded in Django + live prediction .......... (3)
- [x] DRF endpoints + Postman collection ............. (2)
- [~] README + requirements.txt + viva prep .......... (2 + 4)  # docs done; fill CONTRIBUTIONS.md names + viva practice

### Admin login (dev)
Username: `admin`   Password: `admin12345`   (change before submission)
