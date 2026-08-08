import logging

import phonenumbers
from django.db import migrations

logger = logging.getLogger(__name__)

# Mirrors apps.users.services.normalize_phone/PHONE_DEFAULT_REGION, but
# reimplemented here rather than imported — a migration needs to keep
# working exactly as written even if that function's behavior changes
# later, so it can't depend on it.
PHONE_DEFAULT_REGION = "LB"


def normalize_or_none(raw):
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw, PHONE_DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def normalize_phones(apps, schema_editor):
    User = apps.get_model('users', 'User')

    seen = {}  # normalized number -> user id that claimed it
    # Includes '' (blank-but-not-null), not just non-empty values — those
    # predate 0005 making the field nullable, and need to become NULL too,
    # or several of them collide with each other as soon as 0007 adds the
    # uniqueness constraint (multiple rows all equal to '').
    for user in User.objects.exclude(phone__isnull=True):
        canonical = normalize_or_none(user.phone)
        if canonical is None:
            logger.warning(
                "Clearing unparseable phone %r on user id=%s during normalization.",
                user.phone, user.pk,
            )
        elif canonical in seen:
            # Two real accounts already carry the same number in different
            # clothing (e.g. "70123456" vs "+96170123456") — this is
            # exactly the case a unique constraint is meant to catch, but
            # it must be resolved by a human, not guessed at here. Failing
            # the migration surfaces it instead of silently picking one
            # side or corrupting data at the row that happened to sort
            # first.
            raise RuntimeError(
                f"Phone normalization collision: user id={user.pk} and "
                f"user id={seen[canonical]} both normalize to {canonical!r}. "
                "Resolve by clearing/correcting one of them, then re-run."
            )
        else:
            seen[canonical] = user.pk

        if canonical != user.phone:
            user.phone = canonical
            user.save(update_fields=['phone'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_phone_nullable'),
    ]

    operations = [
        migrations.RunPython(normalize_phones, migrations.RunPython.noop),
    ]
