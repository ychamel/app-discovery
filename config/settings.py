"""
Django settings for the Curated App Discovery Platform.

Configuration is read from the environment (12-factor): secrets and the database
connection never live in code. For local development a `.env` file at the repo
root is loaded if present — see `.env.example` for the full set of variables.

Tunable *application* values (token TTLs, rate limits) do NOT live here — they are
owned by `apps.core.config` so there is one typed source of truth for them.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    """Populate os.environ from a simple KEY=VALUE `.env` file, if it exists.

    Intentionally tiny and dependency-free: existing environment variables win
    (so real env always overrides the file), blank lines and `#` comments are
    skipped, and surrounding quotes are stripped. This is a dev convenience; in
    production the environment is set by the platform, not by a file.
    """
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str | None = None, *, required: bool = False) -> str | None:
    """Read an environment variable, failing loudly when a required one is absent."""
    value = os.environ.get(key, default)
    if required and value is None:
        raise RuntimeError(
            f"Required environment variable {key!r} is not set. "
            f"See .env.example for the variables this project needs."
        )
    return value


def env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", default=False)

# In production SECRET_KEY is required; in DEBUG we allow an ephemeral dev key so
# `manage.py check`/`runserver` work out of the box without secret provisioning.
SECRET_KEY = env("DJANGO_SECRET_KEY", required=not DEBUG) or "dev-insecure-key-not-for-production"

ALLOWED_HOSTS = [h for h in (env("DJANGO_ALLOWED_HOSTS", "") or "").split(",") if h]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


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
    "rest_framework",
    "apps.core",
    "apps.accounts",
    "apps.taxonomy",
    "apps.catalog",
    "apps.signals",
    "apps.pages",
    "apps.ratings",
    "apps.subscriptions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # After auth so request.user is resolvable for log correlation (DESIGN.md §10).
    "apps.core.middleware.RequestContextMiddleware",
    # After auth + request-context so visits attribute to request.user and failures log
    # with request context (signal-capture DESIGN.md §5d/§12). Fail-soft-but-counted.
    "apps.signals.middleware.PlatformVisitMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# Database — PostgreSQL only (citext + UUID rely on it; see DESIGN.md §4)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "identity"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD", ""),
        # HOST may be a hostname or, for a local unix socket, a directory path.
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
    }
}


# ---------------------------------------------------------------------------
# Authentication & sessions
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.Account"

# Server-side sessions backed by the database (survive process restarts; no
# in-memory auth state — DESIGN.md §4 crash/restart).
SESSION_ENGINE = "django.contrib.sessions.backends.db"

LOGIN_URL = "/auth/signin"

AUTH_PASSWORD_VALIDATORS: list[dict] = []  # passwordless (magic-link); see DESIGN.md §8


# ---------------------------------------------------------------------------
# Security posture (DESIGN.md §10)
# ---------------------------------------------------------------------------
# Cookie protections that work on any transport are always on.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# CSRF is enforced for all form posts by CsrfViewMiddleware (installed above);
# the templates include {% csrf_token %}.

# HTTPS-dependent protections: on in real deployments, off under local http (DEBUG).
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
# Trust the proxy's X-Forwarded-Proto so SSL redirect/secure cookies work behind a TLS proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# HSTS only when serving HTTPS, to avoid locking out local http development.
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # one year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ---------------------------------------------------------------------------
# Django REST Framework — JSON contracts for downstream consumers
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "UNAUTHENTICATED_USER": None,
}


# ---------------------------------------------------------------------------
# Email — pluggable transport (DESIGN.md §6); console in dev.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@app-discovery.local")
# Base URL used to build absolute magic-link URLs in emails.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Internationalization & static files
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Uploaded app screenshots live under MEDIA_ROOT and are served at MEDIA_URL
# (submission-intake DESIGN.md §9). The numeric size/count limits are typed tunables
# in apps.core.config, not settings, so they share one validated source of truth.
MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT") or str(BASE_DIR / "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Logging (DESIGN.md §10) — structured lines carrying request id + account UUID.
# Application logs identify the actor by UUID only; raw email never appears.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {
            "()": "apps.core.observability.RequestContextFilter",
        },
    },
    "formatters": {
        "structured": {
            "format": (
                "level=%(levelname)s logger=%(name)s request_id=%(request_id)s "
                "account_id=%(account_id)s msg=%(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_context"],
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
