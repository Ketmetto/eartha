from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


@shared_task
def send_transactional_email(to_email: str, subject: str, message: str = "", template_name: str = None, context: dict = None):
    """
    Send a transactional email.

    Legacy usage: pass message as plain text.
    Template usage: pass template_name (without extension) and context dict.
    Renders both .txt and .html versions if templates exist.
    """
    if template_name and context is not None:
        # Try to render HTML version
        html_message = None
        try:
            html_message = render_to_string(f"{template_name}.html", context)
        except Exception:
            pass  # HTML template optional

        # Try to render text version
        try:
            text_message = render_to_string(f"{template_name}.txt", context)
        except Exception:
            text_message = message or ""  # fallback to plain message

        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[to_email],
            html_message=html_message,
        )
    else:
        # Legacy plain-text path
        send_mail(subject, message, settings.EMAIL_HOST_USER, [to_email])


@shared_task
def notify_points_awarded(user_id, points: int):
    """Called by apps.points.services after a successful award."""
    # fetch user, render template, call send_transactional_email.delay(...)
    pass


@shared_task
def notify_submission_status_changed(submission_id, new_status: str):
    """Called by apps.submissions.services on accept/reject/dispatch."""
    pass
