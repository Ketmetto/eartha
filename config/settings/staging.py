from .base import *  # noqa

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

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

# Same baseline hardening as prod — staging is client-facing too. No SSL
# redirect here since staging may sit behind a proxy that already
# terminates TLS and forwards plain HTTP internally (an SSL_REDIRECT would
# risk a redirect loop in that case). Cookie security doesn't have that
# risk — a Secure-flagged cookie is safe regardless of how TLS gets
# terminated — so unlike SSL_REDIRECT there's no reason to skip it if
# staging is served over HTTPS at all, which the "client-facing" framing
# above implies it is.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Same static-serving story as prod.py — gunicorn doesn't serve /static/
# on its own, WhiteNoiseMiddleware (in base.py) does, backed by this
# compressed + hashed-filename storage.
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
