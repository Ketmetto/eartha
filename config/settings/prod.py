from .base import *  # noqa

import sentry_sdk
from csp.constants import NONCE, NONE, SELF, UNSAFE_INLINE
from sentry_sdk.integrations.django import DjangoIntegration

# CSPMiddleware just adds a response header — safe to slot in right after
# SecurityMiddleware, which handles the other security headers.
# AdminCSPMiddleware must come after CSPMiddleware — see its docstring —
# so it's inserted one further down.
MIDDLEWARE = MIDDLEWARE.copy()
security_index = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
MIDDLEWARE.insert(security_index + 1, "csp.middleware.CSPMiddleware")
MIDDLEWARE.insert(security_index + 2, "base.middleware.AdminCSPMiddleware")

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
    "https://eartha.me",
    "https://www.eartha.me",
]

# Baseline hardening
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Every page's inline <script> blocks (see apps/web templates) carry
# nonce="{{ request.csp_nonce }}", which CSPMiddleware fills in per-request
# — that's what NONCE below wires up. Firebase (Google sign-in) and Google
# Maps (address autocomplete) are the only third-party script/XHR origins
# the frontend actually uses; everything else is same-origin.
# style-src stays on UNSAFE_INLINE rather than nonces: the templates lean
# on plain style="..." attributes throughout (not just <style> blocks), and
# nonces don't cover the attribute form. CSS injection is a much lower-severity
# risk than script injection, so this is an accepted tradeoff, not an oversight.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, NONCE, "https://www.gstatic.com", "https://maps.googleapis.com", "https://apis.google.com"],
        "style-src": [SELF, UNSAFE_INLINE, "https://fonts.googleapis.com"],
        "font-src": [SELF, "https://fonts.gstatic.com"],
        # TODO: once AWS_STORAGE_BUCKET_NAME is set for real (see
        # DEPLOYMENT-KEYS-AND-ISSUES.md), add that bucket's domain here —
        # until then media is same-origin, so this is all that's needed.
        # blob: is for the voucher QR code — fetchRedemptionQrObjectUrl()
        # fetches the PNG with a JWT header (plain <img src> can't carry
        # one) and points the <img> at a URL.createObjectURL() blob instead.
        "img-src": [SELF, "data:", "blob:", "https://*.googleapis.com", "https://*.gstatic.com"],
        "connect-src": [SELF, "https://identitytoolkit.googleapis.com", "https://securetoken.googleapis.com", "https://maps.googleapis.com"],
        # Firebase's signInWithPopup loads a relay iframe from the auth
        # helper (apis.google.com) and from the project's authDomain.
        "frame-src": [SELF, "https://apis.google.com", "https://eartha-d3fcb.firebaseapp.com", "https://accounts.google.com"],
        "object-src": [NONE],
        "base-uri": [SELF],
        "frame-ancestors": [NONE],
    },
}

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
