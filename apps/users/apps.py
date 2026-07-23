import json

from decouple import config
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"

    def ready(self):
        raw = config("FIREBASE_SERVICE_ACCOUNT_JSON", default="")
        if not raw:
            return

        import firebase_admin
        from firebase_admin import credentials

        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
