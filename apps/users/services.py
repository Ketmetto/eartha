"""
Business logic for user/profile operations that's more than a single
model save — kept here so views and other apps' services call this,
not User.objects directly.
"""
from .models import User


def get_or_create_notification_prefs(user: User):
    from .models import NotificationPreference
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return prefs


def get_or_create_address(user: User):
    from .models import Address
    address, _ = Address.objects.get_or_create(user=user)
    return address


def change_password(user: User, new_password: str) -> None:
    """
    Caller (ChangePasswordSerializer) has already verified old_password
    and that new_password passed Django's validators — this just does
    the actual mutation, kept separate so it's the one place password
    changes happen and can be extended later (e.g. invalidate other
    sessions, send a security notification email).
    """
    user.set_password(new_password)
    user.save(update_fields=["password"])
