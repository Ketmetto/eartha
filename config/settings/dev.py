from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Fall back to printing emails to the console when no real SMTP host is
# configured, so dev doesn't need a provider to boot. Set EMAIL_HOST (and
# friends) in .env to send through a real provider instead.
if not EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Session auth (in addition to JWT) so the DRF browsable API's login page
# works — lets you click through the API in a plain browser tab instead of
# needing to attach a JWT bearer header by hand. Dev-only, real API clients
# still use JWT.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
}
