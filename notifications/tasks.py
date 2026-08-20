import logging

from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def send_transactional_email(to_email: str, subject: str, message: str = "", template_name: str = None, context: dict = None):
    """
    Send a transactional email.

    Legacy usage: pass message as plain text.
    Template usage: pass template_name (without extension) and context dict.
    Renders both .txt and .html versions if templates exist.

    IMPORTANT: the .txt template is rendered through the same Django
    template engine as every HTML page, which autoescapes by default
    regardless of file extension — a context value containing "&" (e.g.
    a query-string URL like "?uid=x&token=y") renders as "&amp;" in the
    plain-text body, which breaks the link if a client pastes it as a
    literal URL. Any new .txt template that interpolates a URL needs to
    wrap its body in {% autoescape off %}...{% endautoescape %} (see
    verify_email.txt / password_reset.txt / confirm_email_change.txt for
    the pattern) — don't disable autoescape at the engine level in
    settings.py to "fix" this, since that engine also renders every
    user-facing HTML page and would reopen it to XSS.
    """
    if template_name and context is not None:
        html_message = None
        try:
            html_message = render_to_string(f"{template_name}.html", context)
        except Exception:
            logger.warning("No HTML template for %r, sending text-only", template_name)

        try:
            text_message = render_to_string(f"{template_name}.txt", context)
        except Exception:
            logger.exception("Failed to render text template %r, falling back to plain message", template_name)
            text_message = message or ""

        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
        )
    else:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])


@shared_task
def notify_points_awarded(user_id, points: int):
    """Called by apps.points.services after a successful award."""
    from django.contrib.auth import get_user_model
    from django.db.models import Sum
    from apps.points.models import PointsLedgerEntry

    from apps.users.services import get_or_create_notification_prefs

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    if not get_or_create_notification_prefs(user).email_enabled:
        return

    balance = PointsLedgerEntry.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0
    entry = (
        PointsLedgerEntry.objects.filter(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD)
        .order_by("-created_at")
        .first()
    )

    send_transactional_email(
        to_email=user.email,
        subject="You just earned points",
        template_name="points_awarded",
        context={
            "first_name": user.first_name,
            "email": user.email,
            "points": points,
            "balance": balance,
            "category": getattr(entry.reference_item, "category", "") if entry else "",
            "condition": getattr(entry.reference_item, "condition", "") if entry else "",
            "profile_url": f"{settings.SITE_URL}/profile/",
        },
    )


@shared_task
def notify_admin_of_new_submission(item_id):
    """Called by apps.submissions.services.create_item_with_photos —
    an operational alert, not a user-facing/preference-gated email like
    notify_submission_status_changed, so it always fires."""
    from apps.submissions.models import Item

    try:
        item = Item.objects.select_related("user").get(pk=item_id)
    except Item.DoesNotExist:
        return

    submitter = item.user.first_name or item.user.email
    subject = f"New submission: {item.get_category_display()} ({item.get_condition_display()})"
    review_url = f"{settings.SITE_URL}/queue/#item-{item.id}"
    message = (
        f"{submitter} submitted a {item.get_category_display()} ({item.get_condition_display()} condition) item for review.\n\n"
        f"Review it here: {review_url}"
    )

    send_transactional_email(to_email="info@eartha.me", subject=subject, message=message)


@shared_task
def notify_submission_status_changed(submission_id, new_status: str):
    """Called by apps.submissions.services on accept/reject/dispatch."""
    from apps.submissions.models import Item

    try:
        item = Item.objects.select_related("user").get(pk=submission_id)
    except Item.DoesNotExist:
        return

    from apps.users.services import get_or_create_notification_prefs

    user = item.user
    if not get_or_create_notification_prefs(user).email_enabled:
        return

    send_transactional_email(
        to_email=user.email,
        subject="Your submission status changed",
        template_name="submission_status_changed",
        context={
            "first_name": user.first_name,
            "email": user.email,
            "category": item.category,
            "created_at": item.created_at,
            "status_label": item.get_status_display(),
            "rejection_reason": item.rejection_reason,
            "profile_url": f"{settings.SITE_URL}/profile/",
        },
    )
