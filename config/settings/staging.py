from .base import *  # noqa

DEBUG = False

# Same baseline hardening as prod — staging is client-facing too. No SSL
# redirect here since staging may sit behind a proxy that already
# terminates TLS and forwards plain HTTP internally.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
