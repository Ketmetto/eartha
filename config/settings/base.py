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
    "apps.content",
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
                    {"title": _("Drivers"), "icon": "badge", "link": reverse_lazy("admin:submissions_driver_changelist")},
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
        # Per-account, on top of "login"'s per-IP cap — stops a distributed
        # (many-IPs) attacker from getting unlimited guesses at one account.
        "login_account": "10/hour",
        # Shared across resend-verification, password-reset-request, and
        # password-reset-confirm — a single reset already costs 2 of these
        # (request + confirm), so 5 was too tight for legit retry behavior
        # (e.g. fumbling the new password once and needing another attempt).
        "email_action": "10/hour",
        # Public and fires a real email to the admin on every submission —
        # the generic "anon" rate is too loose for that combination.
        "contact": "5/hour",
        # Public and can trigger a welcome email (first signup per address
        # only) — same reasoning as "contact".
        "newsletter": "5/hour",
        # Generous for one real donation-photography session, well under
        # the "user" default's 10,000-photos/hour ceiling (10 per request).
        "item_upload": "30/hour",
        # redeem_benefit is already race-safe; this just caps a scripted
        # hammering attempt well below any real redemption session's needs.
        "redeem": "20/hour",
        # Public, no-auth — the merchant-facing voucher check/redeem. The
        # code's random suffix is only 5 hex chars (~1M combos per benefit
        # prefix), so this can't be as loose as "anon"; a busy store
        # scanning many customers back-to-back still needs headroom.
        # Per-IP, so one store's traffic doesn't cap another's.
        "verify": "60/hour",
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
# Nothing reads task results; storing them just fills Redis (see the
# maxmemory-policy note in docker-compose.prod.yml).
CELERY_TASK_IGNORE_RESULT = True
# Ack only after the task finishes, so an email task in flight when the
# worker is OOM-killed or restarted gets redelivered instead of dropped.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# --- Email ---
# Absolute base URL for links inside emails sent from Celery tasks (e.g.
# notify_points_awarded), which have no request object to build one from
# the way apps/users/services.py's auth-flow emails do.
SITE_URL = config("SITE_URL", default="http://localhost:8000").rstrip("/")

# EMAIL_BACKEND defaults to real SMTP; dev.py overrides to console unless
# EMAIL_HOST is configured (e.g. for testing against a real provider).
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="")
# SMTP auth username — provider-specific, not necessarily an email address
# (e.g. Brevo issues a generated xxxxxx001@smtp-brevo.com login, SendGrid
# uses the literal string "apikey"). Use DEFAULT_FROM_EMAIL below for the
# visible sender.
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
# Django's default is no timeout: a hung SMTP connection would pin one of
# the worker's two slots indefinitely, stalling every email queued behind it.
EMAIL_TIMEOUT = 30
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="")

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'