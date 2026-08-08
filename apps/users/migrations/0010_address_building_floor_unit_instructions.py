from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_lowercase_user_emails'),
    ]

    operations = [
        # line2 was in the model but never exposed anywhere in the UI —
        # confirmed blank on every existing row before renaming, so this
        # loses nothing. "building" is what it was always meant for.
        migrations.RenameField(
            model_name='address',
            old_name='line2',
            new_name='building',
        ),
        migrations.AddField(
            model_name='address',
            name='floor_unit',
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AddField(
            model_name='address',
            name='instructions',
            field=models.TextField(blank=True),
        ),
    ]
