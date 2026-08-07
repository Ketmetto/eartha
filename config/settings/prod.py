from .base import *  # noqa

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

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

# gunicorn alone doesn't serve /static/ — WhiteNoiseMiddleware (in base.py)
# does that, backed by this compressed + hashed-filename storage so static
# assets can be cached forever by the browser/CDN without stale-asset risk
# on deploy. Dev keeps the plain StaticFilesStorage from base.py: the
# manifest variant is strict about every referenced file actually existing
# after collectstatic, which just adds friction for local iteration.
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Fall back to local disk when no S3-compatible bucket is configured yet —
# same fallback dev.py uses. Without it, base.py's S3Boto3Storage tries to
# build a boto3 client with an empty endpoint/bucket and raises
# "ValueError: Invalid endpoint" the moment any FileField/ImageField (e.g.
# a benefit logo) is serialized, taking down the whole request. Set
# AWS_STORAGE_BUCKET_NAME (and friends) in .env.prod to switch to real S3.
if not AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        **STORAGES,
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    }
