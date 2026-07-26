from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from base.models import BaseModel


class User(AbstractUser):
    """Custom user so we can add fields later without a painful migration."""
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True)
    verified = models.BooleanField(
        default=False,
        help_text="Manually verified accounts skip email verification on login. Used to grant access to test accounts.",
    )

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
# or social login. Email verification status is tracked here too — social
# logins (see apps/users/services.py) flip it to True after creation.
#
# Only touches `verified` on creation or when the email actually changes —
# it must NOT reset on every save, or an unrelated profile edit (e.g. a
# MeView PATCH) would silently un-verify an already-verified address.

@receiver(post_save, sender=User)
def sync_email_address(sender, instance, created, **kwargs):
    if not instance.email:
        return
    from allauth.account.models import EmailAddress
    if created:
        EmailAddress.objects.update_or_create(
            user=instance,
            defaults={"email": instance.email, "primary": True, "verified": False},
        )
        return
    email_address, _ = EmailAddress.objects.get_or_create(
        user=instance,
        defaults={"email": instance.email, "primary": True, "verified": False},
    )
    if email_address.email != instance.email:
        email_address.email = instance.email
        email_address.verified = False
        email_address.save()
