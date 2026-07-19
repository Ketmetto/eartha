from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
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


# --- allauth EmailAddress sync ---
# Keeps EmailAddress in sync with User.email so the admin table shows
# all users regardless of whether they signed up via custom registration
# or social login. Email verification status is tracked here too.

@receiver(post_save, sender=User)
def sync_email_address(sender, instance, created, **kwargs):
    if not instance.email:
        return
    from allauth.account.models import EmailAddress
    EmailAddress.objects.update_or_create(
        user=instance,
        defaults={
            "email": instance.email,
            "primary": True,
            # Custom-registered users start unverified; social users
            # will have this flipped to True by allauth's adapter.
            "verified": False,
        },
    )
