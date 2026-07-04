"""
Django settings for the Real-Time Environmental Health Monitoring &
Air Quality Prediction Dashboard.

Secrets and environment-specific values are loaded from a .env file
(see .env.example) so nothing sensitive lives in source control.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the project-root .env file.
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    """Small helper to read an environment variable with a fallback."""
    value = os.getenv(key)
    return value if value not in (None, "") else default


def env_bool(key, default=False):
    return str(env(key, default)).lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", "django-insecure-dev-key-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "django_apscheduler",

    # Project apps
    "dashboard",
    "data_api",
    "predictor",
    "reports",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Database (PostgreSQL) — Guideline 3.3
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "air_quality_db"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
    }
}


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"          # IQAir timestamps are UTC; store in UTC, localize in views
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Authentication redirects (reports app handles login)
# ---------------------------------------------------------------------------
LOGIN_URL = "reports:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "reports:login"


# ---------------------------------------------------------------------------
# Django REST Framework — Guideline 3.6
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}


# ---------------------------------------------------------------------------
# IQAir AirVisual API + monitoring config (read from .env)
# ---------------------------------------------------------------------------
AIRVISUAL_API_KEY = env("AIRVISUAL_API_KEY", "")
AIRVISUAL_BASE_URL = "https://api.airvisual.com/v2"
FETCH_INTERVAL_MINUTES = int(env("FETCH_INTERVAL_MINUTES", "5"))


def _parse_locations(raw):
    """Parse 'City,State,Country[,lat,lon];...' into a list of dicts.

    Latitude/longitude are optional (used for the map + Open-Meteo enrichment).
    """
    locations = []
    for chunk in (raw or "").split(";"):
        parts = [p.strip() for p in chunk.split(",")]
        if len(parts) >= 3 and all(parts[:3]):
            loc = {"city": parts[0], "state": parts[1], "country": parts[2]}
            if len(parts) >= 5:
                try:
                    loc["lat"] = float(parts[3])
                    loc["lon"] = float(parts[4])
                except ValueError:
                    pass
            locations.append(loc)
    return locations


AQ_LOCATIONS = _parse_locations(env(
    "AQ_LOCATIONS",
    "Kigali,Kigali,Rwanda,-1.9499,30.0588;Delhi,Delhi,India,28.6667,77.1167",
))

# city -> (lat, lon) for the map + Open-Meteo enrichment
CITY_COORDS = {
    loc["city"]: (loc.get("lat"), loc.get("lon"))
    for loc in AQ_LOCATIONS
    if loc.get("lat") is not None
}
