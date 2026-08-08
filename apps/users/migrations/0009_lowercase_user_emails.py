from django.db import migrations


def lowercase_emails(apps, schema_editor):
    User = apps.get_model('users', 'User')

    seen = {}  # lowercased email -> user id that claimed it
    for user in User.objects.all():
        canonical = user.email.strip().lower()
        if canonical in seen and seen[canonical] != user.pk:
            # Same shape as the phone migration's collision guard: two
            # accounts already differing only by case is a real conflict
            # (which one is "the" account? which one keeps login access?)
            # that needs a human decision, not a guess made mid-migration.
            raise RuntimeError(
                f"Email lowercasing collision: user id={user.pk} and "
                f"user id={seen[canonical]} both normalize to {canonical!r}. "
                "Resolve by renaming/merging one of them, then re-run."
            )
        seen[canonical] = user.pk
        if canonical != user.email:
            user.email = canonical
            user.save(update_fields=['email'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_phone_unique'),
    ]

    operations = [
        migrations.RunPython(lowercase_emails, migrations.RunPython.noop),
    ]
