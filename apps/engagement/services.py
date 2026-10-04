from django.conf import settings

from notifications.tasks import send_transactional_email


def notify_admin_of_contact_message(message):
    subject = f"New {'partner inquiry' if message.is_partner_inquiry else 'contact message'}: {message.subject or 'no subject'}"
    send_transactional_email.delay("info@eartha.me", subject, message.message)


def subscribe_to_newsletter(email):
    """Idempotent — only a brand-new address gets the welcome email, so
    resubmitting the form (or someone typing a stranger's address over and
    over) can't be used to flood an inbox."""
    from .models import NewsletterSubscriber

    _, created = NewsletterSubscriber.objects.get_or_create(email=email)
    if created:
        send_transactional_email.delay(
            to_email=email,
            subject="You're subscribed to the Eartha newsletter",
            template_name="newsletter_welcome",
            context={"email": email, "site_url": settings.SITE_URL},
        )
    return created
