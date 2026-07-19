from django.contrib.auth.models import AbstractUser
from django.db import models
from base.models import BaseModel


class User(AbstractUser):
    """Custom user so we can add fields later without a painful migration."""
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]


class Address(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="address")
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20, blank=True)


class NotificationPreference(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_prefs")
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
