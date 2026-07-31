"""
Shared settings. Environment-specific files (dev.py, staging.py, prod.py)
import * from here and override what's different.
"""
from pathlib import Path
from decouple import config, Csv
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())

# Firebase's signInWithPopup relies on window.opener to relay the auth
# result back; Django's default COOP ("same-origin") severs that link.
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

INSTALLED_APPS = [
    # unfold must load before django.contrib.admin — it overrides admin's
    # templates/static, and Django resolves both by app-loading order.
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "dj_rest_auth",
    "storages",

    # local apps
    "base",
    "notifications",
    "apps.users",
    "apps.submissions",
    "apps.points",
    "apps.engagement",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "notifications" / "templates"],
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB"),
        "USER": config("POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1

# --- Admin theme (django-unfold) ---
# Color ramp derived from the brand's --ok green (#4A5D3A, see app.css) so
# the admin doesn't look like an unrelated third-party skin.
UNFOLD = {
    "SITE_TITLE": "Eartha Admin",
    "SITE_HEADER": "Eartha",
    "SITE_SYMBOL": "eco",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "247 250 245",
            "100": "237 242 232",
            "200": "216 228 206",
            "300": "187 207 170",
            "400": "151 177 129",
            "500": "117 148 92",
            "600": "95 119 74",
            "700": "77 97 61",
            "800": "62 79 49",
            "900": "50 63 39",
            "950": "32 41 25",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Overview"),
                "items": [
                    {"title": _("Dashboard"), "icon": "dashboard", "link": reverse_lazy("admin:index")},
                ],
            },
            {
                "title": _("Users"),
                "items": [
                    {"title": _("Users"), "icon": "group", "link": reverse_lazy("admin:users_user_changelist")},
                    {"title": _("Addresses"), "icon": "location_on", "link": reverse_lazy("admin:users_address_changelist")},
                    {"title": _("Notification prefs"), "icon": "notifications", "link": reverse_lazy("admin:users_notificationpreference_changelist")},
                ],
            },
            {
                "title": _("Submissions"),
                "items": [
                    {"title": _("Items"), "icon": "inventory_2", "link": reverse_lazy("admin:submissions_item_changelist")},
                    {"title": _("Driver assignments"), "icon": "local_shipping", "link": reverse_lazy("admin:submissions_driverassignment_changelist")},
                ],
            },
            {
                "title": _("Points & benefits"),
                "items": [
                    {"title": _("Points ledger"), "icon": "toll", "link": reverse_lazy("admin:points_pointsledgerentry_changelist")},
                    {"title": _("Benefits"), "icon": "redeem", "link": reverse_lazy("admin:points_benefit_changelist")},
                    {"title": _("Redemptions"), "icon": "shopping_bag", "link": reverse_lazy("admin:points_redemption_changelist")},
                ],
            },
            {
                "title": _("Engagement"),
                "items": [
                    {"title": _("Contact messages"), "icon": "mail", "link": reverse_lazy("admin:engagement_contactmessage_changelist")},
                    {"title": _("Impact stats"), "icon": "insights", "link": reverse_lazy("admin:engagement_impactstat_changelist")},
                ],
            },
            {
                "title": _("Access control"),
                "items": [
                    {"title": _("Groups"), "icon": "shield", "link": reverse_lazy("admin:auth_group_changelist")},
                ],
            },
        ],
    },
}

# --- Cache (backs DRF throttling — shared across workers, unlike locmem) ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "KEY_PREFIX": "cache",
    }
}

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "base.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "base.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "register": "10/hour",
        "login": "20/hour",
        "email_action": "5/hour",
    },
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=Csv())

# --- Social login (dj-rest-auth + allauth), returns JWTs like normal login ---
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,
    "TOKEN_MODEL": None,  # JWT-only; skip DRF's authtoken app entirely
}
REST_SESSION_LOGIN = False

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID", default=""),
            "secret": config("GOOGLE_CLIENT_SECRET", default=""),
            "key": "",
        }
    },
    "apple": {
        "APP": {
            "client_id": config("APPLE_CLIENT_ID", default=""),
            "secret": config("APPLE_CLIENT_SECRET", default=""),
            "key": config("APPLE_KEY_ID", default=""),
        }
    },
}

# --- Storage (S3-compatible) ---
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default="")
STORAGES = {
    "default": {"BACKEND": "base.storage.MediaStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --- Celery ---
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# --- Email ---
# EMAIL_BACKEND defaults to real SMTP; dev.py overrides to console unless
# EMAIL_HOST is configured (e.g. for testing against a real provider).
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
# SMTP auth username — for SendGrid this is literally the string "apikey",
# not an email address. Use DEFAULT_FROM_EMAIL below for the visible sender.
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="")

# Points-per-condition criteria: static table for now (see apps/points/rules.py).
# Swap for a configurable rules engine later without touching other modules.

# Keep allauth minimal — only for social
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Don't let allauth interfere with your custom flow
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'