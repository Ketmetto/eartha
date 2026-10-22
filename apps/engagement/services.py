from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.utils import timezone

from base.form_guard import check_form_token, make_form_token
from notifications.tasks import send_transactional_email


def notify_admin_of_contact_message(message):
    subject = f"New {'partner inquiry' if message.is_partner_inquiry else 'contact message'}: {message.subject or 'no subject'}"
    send_transactional_email.delay("info@eartha.me", subject, message.message)


# Same lifetime as Django's password-reset/email-verification tokens.
NEWSLETTER_CONFIRM_MAX_AGE = settings.PASSWORD_RESET_TIMEOUT
NEWSLETTER_CONFIRM_SALT = "engagement.newsletter-confirm"


def subscribe_to_newsletter(email, request=None):
    """Double opt-in, mirroring account signup: store the address
    unconfirmed and email a confirmation link. Resubmitting an unconfirmed
    address resends the link (like resend-verification); an already
    confirmed one gets nothing, so the caller's response never differs."""
    from .models import NewsletterSubscriber

    subscriber, _ = NewsletterSubscriber.objects.get_or_create(email=email)
    if subscriber.confirmed_at is None:
        send_newsletter_confirmation_email(subscriber, request)


def send_newsletter_confirmation_email(subscriber, request=None):
    token = signing.dumps(str(subscriber.pk), salt=NEWSLETTER_CONFIRM_SALT)
    url = f"/newsletter/confirm/?token={token}"
    absolute_url = request.build_absolute_uri(url) if request is not None else f"{settings.SITE_URL}{url}"

    send_transactional_email.delay(
        to_email=subscriber.email,
        subject="Confirm your Eartha newsletter subscription",
        template_name="newsletter_confirm",
        context={"email": subscriber.email, "confirmation_url": absolute_url},
    )


def confirm_newsletter_subscription(token):
    """Validate the emailed token and mark the subscriber confirmed.
    Returns (success, message). Clicking the link twice is fine."""
    from .models import NewsletterSubscriber

    try:
        subscriber_id = signing.loads(token, salt=NEWSLETTER_CONFIRM_SALT, max_age=NEWSLETTER_CONFIRM_MAX_AGE)
        subscriber = NewsletterSubscriber.objects.get(pk=subscriber_id)
    except (signing.BadSignature, NewsletterSubscriber.DoesNotExist, ValueError, ValidationError):
        # SignatureExpired is a BadSignature subclass.
        return False, "Confirmation link expired or invalid. Sign up again to get a new one."

    if subscriber.confirmed_at is None:
        subscriber.confirmed_at = timezone.now()
        subscriber.save(update_fields=["confirmed_at", "updated_at"])
    return True, "You're subscribed to the Eartha newsletter."


WISHLIST_FORM_SALT = "engagement.wishlist-form"


def make_wishlist_form_token():
    return make_form_token(WISHLIST_FORM_SALT)


def check_wishlist_form_token(token):
    """See base.form_guard.check_form_token."""
    return check_form_token(token, WISHLIST_FORM_SALT)


def notify_admin_of_wishlist_request(wishlist_request):
    r = wishlist_request
    lines = [
        f"Organization: {r.organization}",
        f"Contact: {r.contact_name} <{r.email}>" + (f", {r.phone}" if r.phone else ""),
        f"Location: {r.location}" if r.location else None,
        f"Needed by: {r.needed_by:%d %b %Y}" if r.needed_by else None,
        f"Sizes: {r.sizes}" if r.sizes else None,
        f"Quantity: {r.quantity}" if r.quantity else None,
        "",
        r.items_needed,
        "",
        f"Review it here: {settings.SITE_URL}/admin/engagement/wishlistrequest/{r.id}/change/",
    ]
    send_transactional_email.delay(
        "info@eartha.me",
        f"New wishlist request: {r.organization}",
        "\n".join(line for line in lines if line is not None),
    )
