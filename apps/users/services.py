"""Business logic for the users app, kept out of views."""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model

from allauth.account.models import EmailAddress

from notifications.tasks import send_transactional_email

User = get_user_model()


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
            "user": user,
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
