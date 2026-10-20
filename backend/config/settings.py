import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Local dev reads the repo-root .env; on Railway, env vars come from the service settings.
load_dotenv(BASE_DIR.parent / ".env")

DEBUG = os.environ.get("DJANGO_DEBUG") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or ("dev-insecure-key" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is not 1")



def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
# The Vercel frontend calls this API from another origin; local dev goes through the Vite proxy instead.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
# Railway terminates TLS at its proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ORS_API_KEY = os.environ.get("ORS_API_KEY", "")

INSTALLED_APPS = [
    "corsheaders",
    "planner",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",  # plan responses are ~500 KB of route geometry
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Stateless API: no models, so no database.
DATABASES = {}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True
