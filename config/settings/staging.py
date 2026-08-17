from .base import *  # noqa

import sentry_sdk
from csp.constants import NONCE, NONE, SELF, UNSAFE_INLINE
from sentry_sdk.integrations.django import DjangoIntegration

MIDDLEWARE = MIDDLEWARE.copy()
security_index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
MIDDLEWARE.insert(security_index + 1, "csp.middleware.CSPMiddleware")
MIDDLEWARE.insert(security_index + 2, "base.middleware.AdminCSPMiddleware")

# See prod.py's identical block for why this is gated on an env var.
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="staging",
    )

DEBUG = False

# Same baseline hardening as prod. No SSL_REDIRECT — staging may sit
# behind a proxy that already terminates TLS, risking a redirect loop —
# but cookie security has no such risk, so no reason to skip it.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Same policy as prod.py — see that file's comments for the reasoning.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, NONCE, "https://www.gstatic.com", "https://maps.googleapis.com"],
        "style-src": [SELF, UNSAFE_INLINE, "https://fonts.googleapis.com"],
        "font-src": [SELF, "https://fonts.gstatic.com"],
        "img-src": [SELF, "data:", "https://*.googleapis.com", "https://*.gstatic.com"],
        "connect-src": [SELF, "https://identitytoolkit.googleapis.com", "https://securetoken.googleapis.com", "https://maps.googleapis.com"],
        "object-src": [NONE],
        "base-uri": [SELF],
        "frame-ancestors": [NONE],
    },
}

# Same static-serving story as prod.py — gunicorn doesn't serve /static/
# on its own, WhiteNoiseMiddleware (in base.py) does, backed by this
# compressed + hashed-filename storage.
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
