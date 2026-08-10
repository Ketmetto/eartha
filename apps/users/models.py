from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from base.models import BaseModel


class User(AbstractUser):
    """Custom user so we can add fields later without a painful migration."""
    email = models.EmailField(unique=True)
    # null, not just blank — lets multiple users leave this unset without
    # colliding on '' under the uniqueness constraint. Normalized to E.164
    # by apps.users.services.normalize_phone.
    phone = models.CharField(max_length=32, blank=True, null=True, unique=True)
    verified = models.BooleanField(
        default=False,
        help_text="Manually verified accounts skip email verification on login. Used to grant access to test accounts.",
    )
    # Stable Firebase identity (Google/Apple sign-in). Matched on instead
    # of email (freely editable via MeView) — a social-only account has
    # no password, so losing this link would make it unrecoverable.
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True)
    # Unconfirmed pending email change — see apps.users.services.
    # request_email_change. `email` itself only updates once confirmed.
    pending_email = models.EmailField(null=True, blank=True)
    # Banning reuses is_active (already blocks both new logins via
    # authenticate() and existing JWTs via JWTAuthentication.get_user's
    # CHECK_USER_IS_ACTIVE) rather than a separate flag — this just records
    # why, for admins looking at the account later.
    ban_reason = models.TextField(blank=True)
    banned_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    # Normalizes casing on every save, covering every write path in one
    # place — email's unique=True is otherwise a case-sensitive DB
    # constraint ("Jane@x.com" and "jane@x.com" wouldn't collide).
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Address(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="address")
    line1 = models.CharField(max_length=255)
    # Free-text extras Places Autocomplete has no structured slot for, and
    # all optional — a bare line1/city/country is still a complete address.
    building = models.CharField(max_length=255, blank=True)
    floor_unit = models.CharField(max_length=60, blank=True)
    instructions = models.TextField(blank=True)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20, blank=True)
    # Set from the map pin-drop step; optional. 6 decimal places is ~11cm
    # precision.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def as_pickup_text(self):
        """Single-line address for admin display and the driver handoff.
        Excludes `instructions`, which is surfaced as its own field."""
        parts = [self.line1, self.building, self.floor_unit, self.city, self.country, self.postal_code]
        return ", ".join(p for p in parts if p)


class NotificationPreference(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_prefs")
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)


# Keeps allauth's EmailAddress in sync with User.email. Only touches
# `verified` on creation or an actual email change — never on an
# unrelated save, or a MeView PATCH would un-verify the address.
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
