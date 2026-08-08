from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_user_firebase_uid_user_pending_email'),
    ]

    operations = [
        # Split from the uniqueness migration that follows: existing rows
        # need normalizing (0006) before it's safe to add unique=True
        # (0007) — attempting both in one step would apply the constraint
        # before the data underneath it was made to satisfy it.
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
