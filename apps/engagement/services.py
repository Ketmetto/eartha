from notifications.tasks import send_transactional_email


def notify_admin_of_contact_message(message):
    subject = f"New {'partner inquiry' if message.is_partner_inquiry else 'contact message'}: {message.subject or 'no subject'}"
    send_transactional_email.delay("info@eartha.me", subject, message.message)
