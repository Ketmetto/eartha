from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_clear_blank_user_phones'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
    ]
