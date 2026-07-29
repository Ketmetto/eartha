import os
from .base import *  

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


# Local-only testing addition — do NOT deploy this line to the VPS
if os.environ.get("LOCAL_TESTING") == "1":
    CSRF_TRUSTED_ORIGINS.append("https://localhost")

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
