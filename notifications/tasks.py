from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_transactional_email(to_email: str, subject: str, message: str):
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
