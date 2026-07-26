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

# Throttle counts also accumulate *within* one pytest session (there's no
# per-test cache reset the way there is a per-test DB rollback), so many
# tests hitting the same rate-limited endpoint (login/register/etc.) would
# start tripping 429s on each other well before any real abuse. Rate
# limiting is an infra concern, not application logic under test here.
# Views with an explicit throttle_scope (ScopedRateThrottle) ignore
# DEFAULT_THROTTLE_CLASSES, and an empty DEFAULT_THROTTLE_RATES would make
# them raise ImproperlyConfigured (unknown scope) rather than just pass —
# so every scope gets a rate here, just an effectively-unlimited one.
# Write a dedicated test with @override_settings if you specifically need
# to assert real throttling behavior.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {rate_scope: "1000000/second" for rate_scope in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]},
}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
