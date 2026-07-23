"""Business logic for the users app, kept out of views."""
import logging
import uuid

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model

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
    return f"/verify-email?uid={uid}&token={token}"


def send_verification_email(user, request=None):
    """Queue a verification email via Celery."""
    url = get_verification_url(user, request)

    # Build absolute URL if request is provided
    if request is not None:
        absolute_url = request.build_absolute_uri(url)
    else:
        absolute_url = url

    send_transactional_email.delay(
        to_email=user.email,
        subject="Verify your email address",
        template_name="emails/verify_email",
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
        # Mark as verified
        EmailAddress.objects.filter(user=user, email=user.email).update(verified=True)
        return True, "Email verified successfully."
    else:
        return False, "Verification link expired or invalid."


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
    """Find or create the local User for a verified Firebase identity."""
    email = decoded_token["email"]

    user = User.objects.filter(email__iexact=email).first()
    if user:
        return user

    name = (decoded_token.get("name") or display_name or "").strip()
    first_name, _, last_name = name.partition(" ")

    user = User(
        username=generate_unique_username(email),
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    user.set_unusable_password()
    user.save()

    EmailAddress.objects.filter(user=user, email=user.email).update(verified=True)
    return user
