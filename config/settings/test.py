"""
sqlite override so the suite runs without a Postgres service — used only
by CI/local `pytest`, never referenced by Docker or deployment configs.
"""
from .base import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True

# In-process cache instead of the real Redis instance base.py configures —
# throttle counts live in cache, and a real Redis persists across separate
# test runs (unlike the DB, which rolls back per test).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Throttle counts accumulate across the whole pytest session (no per-test
# reset like the DB gets), so tests would start tripping 429s on each
# other. Every scope still needs a rate — an empty DEFAULT_THROTTLE_RATES
# makes a ScopedRateThrottle view raise ImproperlyConfigured rather than
# just pass — so each gets an effectively-unlimited one instead. Use
# @override_settings in a dedicated test to assert real throttling.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {rate_scope: "1000000/second" for rate_scope in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]},
}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
