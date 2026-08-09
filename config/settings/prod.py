from .base import *  # noqa

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# No-op until SENTRY_DSN is set (sentry-sdk is a "prod"-only dependency,
# so this import is safe here but not in dev.py).
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# nginx appends to X-Forwarded-For rather than replacing it (see
# nginx/nginx.conf) — without NUM_PROXIES, DRF's throttles would trust
# whatever the client sends there instead of the last, real address.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "NUM_PROXIES": 1,
}

CSRF_TRUSTED_ORIGINS = [
    "https://localhost",
    "https://YOURDOMAIN.com",
    "https://www.YOURDOMAIN.com",
]

# Baseline hardening — see REMINDERS.txt for the CSP header, which
# needs a dependency decision before it's added on top of this.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# WhiteNoiseMiddleware serves /static/; this hashed-filename storage lets
# it be cached forever without stale-asset risk. Dev keeps the plain
# StaticFilesStorage — the manifest variant's strictness about every
# referenced file existing just adds friction for local iteration.
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Falls back to local disk when no S3 bucket is configured — without it,
# base.py's S3Boto3Storage raises on an empty endpoint the moment any
# FileField is serialized. Set AWS_STORAGE_BUCKET_NAME in .env.prod for real S3.
if not AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        **STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
