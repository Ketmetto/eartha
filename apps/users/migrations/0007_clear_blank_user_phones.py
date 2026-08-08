from django.db import migrations


def clear_blank_phones(apps, schema_editor):
    # Belt-and-suspenders cleanup for databases that already ran 0006
    # before its bug fix (it originally skipped phone='' rows instead of
    # nulling them, which then broke 0008's unique index on a database
    # with more than one such row). On a database applying 0006 fresh
    # (already fixed), this is a no-op — nothing will match.
    User = apps.get_model('users', 'User')
    User.objects.filter(phone='').update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_normalize_user_phone_numbers'),
    ]

    operations = [
        migrations.RunPython(clear_blank_phones, migrations.RunPython.noop),
    ]
