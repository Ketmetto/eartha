"""Business logic for the users app, kept out of views."""
import logging
import uuid

import phonenumbers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from allauth.account.models import EmailAddress

from notifications.tasks import send_transactional_email

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_unique_username(email: str) -> str:
    base = email.split("@")[0]
    username = base
    while User.objects.filter(username=username).exists():
        username = f"{base}-{uuid.uuid4().hex[:6]}"
    return username


# A number typed without a country code is assumed Lebanese local; a
# caller can still type a full "+961..." or other-country number.
PHONE_DEFAULT_REGION = "LB"


def normalize_phone(raw: str) -> str:
    """Canonicalize to E.164 (e.g. "+96170123456") so differently
    formatted input for the same number collapses to one stored value.
    Raises DRF's ValidationError, since the only caller is
    UserSerializer.validate_phone."""
    try:
        parsed = phonenumbers.parse(raw, PHONE_DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        raise ValidationError("Enter a valid phone number.")
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError("Enter a valid phone number.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Generates tokens for email verification. Same mechanism as password reset."""
    def _make_hash_value(self, user, timestamp):
        # Hash on user id, timestamp, and email so the token is invalidated
        # if the email changes.
        email = getattr(user, 'email', '') or ''
        return f"{user.pk}{timestamp}{email}"


email_verification_token = EmailVerificationTokenGenerator()


def get_verification_url(user, request=None):
    """Build the verification URL with uidb64 + token."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    # Frontend should handle this route and call the backend verify endpoint
    return f"/verify-email/?uid={uid}&token={token}"


def send_verification_email(user, request=None):
    """Queue a verification email via Celery."""
    url = get_verification_url(user, request)

    if request is not None:
        absolute_url = request.build_absolute_uri(url)
    else:
        absolute_url = url

    send_transactional_email.delay(
        to_email=user.email,
        subject="Verify your email address",
        template_name="verify_email",
        context={
            "first_name": user.first_name,
            "email": user.email,
            "verification_url": absolute_url,
        },
    )


def verify_email_token(uidb64, token):
    """Validate token and mark email as verified. Returns (success, message)."""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return False, "Invalid verification link."

    if email_verification_token.check_token(user, token):
        EmailAddress.objects.filter(user=user, email=user.email).update(verified=True)
        return True, "Email verified successfully."
    else:
        return False, "Verification link expired or invalid."


class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    """Generates tokens for confirming a pending email change. Hashes on
    pending_email rather than email — so requesting a different change
    invalidates any link already sent for the previous one."""
    def _make_hash_value(self, user, timestamp):
        pending = getattr(user, 'pending_email', '') or ''
        return f"{user.pk}{timestamp}{pending}"


email_change_token = EmailChangeTokenGenerator()


def request_email_change(user, new_email, request=None):
    """
    Starts an email change: the account's real `email` — what social
    login matches against (see get_or_create_user_from_firebase) and
    where password-reset/notification mail goes — does NOT change here.
    Only `pending_email` is set, and a confirmation link is sent to the
    new address; `email` only updates once that link is used. Applying
    the new address immediately, unverified, is exactly what let a typo
    or a bad actor silently reassign an account.
    """
    new_email = (new_email or "").strip().lower()
    if not new_email or new_email == user.email.lower():
        return

    if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
        raise ValidationError("An account with this email already exists.")

    user.pending_email = new_email
    user.save(update_fields=["pending_email"])

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_change_token.make_token(user)
    url = f"/confirm-email-change/?uid={uid}&token={token}"
    absolute_url = request.build_absolute_uri(url) if request is not None else url

    send_transactional_email.delay(
        to_email=new_email,
        subject="Confirm your new email address",
        template_name="confirm_email_change",
        context={
            "first_name": user.first_name,
            "email": new_email,
            "confirmation_url": absolute_url,
        },
    )


def confirm_email_change(uidb64, token):
    """Validate token and apply the pending email change. Returns (success, message)."""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return False, "Invalid confirmation link."

    if not user.pending_email:
        return False, "There's no pending email change for this account."

    if not email_change_token.check_token(user, token):
        return False, "Confirmation link expired or invalid."

    # No separate exists()-then-save pre-check — that's a TOCTOU race.
    # Attempt the save and let the DB's unique constraint be the single
    # source of truth, catching IntegrityError instead of a 500.
    user.email = user.pending_email
    user.pending_email = None
    try:
        with transaction.atomic():
            user.save(update_fields=["email", "pending_email"])
    except IntegrityError:
        return False, "That email is now used by another account."
    EmailAddress.objects.filter(user=user, email=user.email).update(verified=True)
    return True, "Email address updated."


def get_password_reset_url(user, request=None):
    """Build the password reset URL with uidb64 + token. Uses Django's
    stock token generator (hashes on password + last_login), so a token
    is invalidated as soon as it's used or the password changes."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    url = f"/reset-password/?uid={uid}&token={token}"
    return request.build_absolute_uri(url) if request is not None else url


def send_password_reset_email(user, request=None):
    """Queue a password reset email via Celery."""
    send_transactional_email.delay(
        to_email=user.email,
        subject="Reset your password",
        template_name="password_reset",
        context={
            "first_name": user.first_name,
            "email": user.email,
            "reset_url": get_password_reset_url(user, request),
        },
    )


def reset_password_with_token(uidb64, token, new_password):
    """Validate token and set the new password. Returns (success, message)."""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return False, "Invalid reset link."

    if not default_token_generator.check_token(user, token):
        return False, "Reset link expired or invalid."

    user.set_password(new_password)
    user.save()
    return True, "Password reset successfully."


def get_or_create_address(user):
    from .models import Address
    return Address.objects.get_or_create(user=user)[0]


def get_or_create_notification_prefs(user):
    from .models import NotificationPreference
    return NotificationPreference.objects.get_or_create(user=user)[0]


def change_password(user, new_password):
    validate_password(new_password, user)
    user.set_password(new_password)
    user.save()


def ban_user(user, reason=""):
    """Blocks all login — both new password/social logins (authenticate()
    checks is_active) and already-issued JWTs (JWTAuthentication.get_user
    checks it too, on every request) — without touching submissions,
    points, or any other account data."""
    user.is_active = False
    user.ban_reason = reason
    user.banned_at = timezone.now()
    user.save(update_fields=["is_active", "ban_reason", "banned_at"])


def unban_user(user):
    user.is_active = True
    user.ban_reason = ""
    user.banned_at = None
    user.save(update_fields=["is_active", "ban_reason", "banned_at"])


def get_user_stats(users):
    """Submission/redemption counts + points balance for a page of users,
    one grouped query per metric instead of one per user — annotating all
    three onto the User queryset directly would fan out (each reverse FK
    join multiplies the others), so they're computed separately and
    matched up by user id instead, same batching idea as
    apps.submissions.mixins.AwardedTotalsListMixin."""
    from django.db.models import Count, Sum
    from apps.submissions.models import Item
    from apps.points.models import PointsLedgerEntry, Redemption

    user_ids = [u.id for u in users]
    submissions = dict(
        Item.objects.filter(user_id__in=user_ids)
        .values("user_id").annotate(n=Count("id")).values_list("user_id", "n")
    )
    redemptions = dict(
        Redemption.objects.filter(user_id__in=user_ids)
        .values("user_id").annotate(n=Count("id")).values_list("user_id", "n")
    )
    balances = dict(
        PointsLedgerEntry.objects.filter(user_id__in=user_ids)
        .values("user_id").annotate(total=Sum("points")).values_list("user_id", "total")
    )
    return {
        uid: {
            "submissions_count": submissions.get(uid, 0),
            "redemptions_count": redemptions.get(uid, 0),
            "points_balance": balances.get(uid, 0) or 0,
        }
        for uid in user_ids
    }


def verify_firebase_token(id_token):
    """Validate a Firebase ID token (Google/Apple sign-in). Returns (decoded_token, error_message)."""
    import firebase_admin
    from firebase_admin import auth as firebase_auth

    if not id_token:
        return None, "Missing ID token."

    try:
        firebase_admin.get_app()
    except ValueError:
        return None, "Social login is not configured."

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
    except firebase_admin.exceptions.FirebaseError:
        logger.exception("Firebase ID token verification failed")
        return None, "Invalid or expired sign-in token."

    if not decoded_token.get("email_verified"):
        return None, "Your email address is not verified with this provider."

    return decoded_token, None


def get_or_create_user_from_firebase(decoded_token, display_name=""):
    """
    Find or create the local User for a verified Firebase identity.

    Matches on the Firebase UID first — a stable identifier that never
    changes — not on email. Users can freely edit their profile email
    (see request_email_change below); matching by email alone would mean
    the next social login no longer finds the account once that changes,
    creating a duplicate, orphaned one instead.
    """
    uid = decoded_token["uid"]
    # Lowercased mainly so generate_unique_username below derives from a
    # normalized local-part — User.save() would lowercase the stored email
    # regardless, but username generation runs before that save.
    email = decoded_token["email"].strip().lower()

    user = User.objects.filter(firebase_uid=uid).first()
    if user:
        return user

    # First time seeing this Firebase identity. If it matches an existing
    # account by email (e.g. they registered with a password first, this
    # is their first Google sign-in), link it there instead of creating a
    # duplicate; otherwise this is a brand new user.
    user = User.objects.filter(email__iexact=email).first()
    if user:
        if not user.firebase_uid:
            user.firebase_uid = uid
            user.save(update_fields=["firebase_uid"])
        return user

    name = (decoded_token.get("name") or display_name or "").strip()
    first_name, _, last_name = name.partition(" ")

    user = User(
        username=generate_unique_username(email),
        email=email,
        first_name=first_name,
        last_name=last_name,
        firebase_uid=uid,
    )
    user.set_unusable_password()
    user.save()

    EmailAddress.objects.filter(user=user, email=user.email).update(verified=True)
    return user
