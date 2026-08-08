from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from base.models import BaseModel


class User(AbstractUser):
    """Custom user so we can add fields later without a painful migration."""
    email = models.EmailField(unique=True)
    # null (not just blank) so multiple users can each leave this unset
    # without colliding on '' under the uniqueness constraint below. Always
    # stored in E.164 — see apps.users.services.normalize_phone — so that
    # "(961) 70 123 456", "70123456" and "+961 70 123 456" are recognized
    # as the same number instead of three distinct strings all satisfying
    # uniqueness.
    phone = models.CharField(max_length=32, blank=True, null=True, unique=True)
    verified = models.BooleanField(
        default=False,
        help_text="Manually verified accounts skip email verification on login. Used to grant access to test accounts.",
    )
    # Stable Firebase identity (Google/Apple sign-in), set on first social
    # login and never changed after. apps.users.services.
    # get_or_create_user_from_firebase matches on this first — not on
    # email, which the user can freely edit via MeView. Matching on email
    # alone meant editing your profile email broke the link to your
    # Firebase identity: the next social login wouldn't find your account
    # (its email no longer matched what the provider sent) and silently
    # created a new, empty one instead, orphaning everything under the old
    # account — which, for a social-only account, has no password either,
    # so it becomes unrecoverable without admin intervention.
    firebase_uid = models.CharField(max_length=128, unique=True, null=True, blank=True)
    # A requested-but-unconfirmed new email — see apps.users.services.
    # request_email_change/confirm_email_change. The address on `email`
    # itself (what social login matches against, and what receives
    # password-reset / notification mail) only changes once the user
    # clicks the confirmation link sent to this address.
    pending_email = models.EmailField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    # There are three separate places a User's email first gets set
    # (RegisterSerializer.create, get_or_create_user_from_firebase, Django
    # admin edits) plus request_email_change's own careful lowercasing —
    # normalizing here once, on every save, is the one place that
    # guarantees "Jane@Example.com" and "jane@example.com" can't both end
    # up stored (email's unique=True is otherwise a case-sensitive DB
    # constraint, same gap phone had before apps.users.services.
    # normalize_phone).
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Address(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="address")
    line1 = models.CharField(max_length=255)
    # Free-text extras Places Autocomplete has no structured slot for —
    # Lebanese addressing commonly identifies a pickup by building name
    # rather than street number, so these matter more here than in most
    # places. All optional; a bare line1/city/country is still a complete
    # address.
    building = models.CharField(max_length=255, blank=True)
    floor_unit = models.CharField(max_length=60, blank=True)
    instructions = models.TextField(blank=True)
    city = models.CharField(max_length=120)
    country = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20, blank=True)
    # Set together from the map pin-drop confirmation step (Places
    # Autocomplete's geocoded location, refined by dragging the marker) —
    # blank for addresses saved before that existed. 6 decimal places is
    # ~11cm precision, the standard for this kind of pin location.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def as_pickup_text(self):
        """Single-line address for admin display and the driver handoff
        (pickup_address_snapshot, WhatsApp dispatch message) — the one
        place this formatting lives, so it can't drift out of sync between
        the two callers the way line1/line2/city/country/postal_code did
        before this method existed. Doesn't include `instructions` —
        driver-facing notes are surfaced as their own field so they can't
        get lost inside a long comma-joined line."""
        parts = [self.line1, self.building, self.floor_unit, self.city, self.country, self.postal_code]
        return ", ".join(p for p in parts if p)


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
