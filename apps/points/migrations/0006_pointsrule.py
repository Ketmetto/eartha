import uuid

from django.db import migrations, models


# Mirrors the static table apps.points.rules.POINTS_TABLE used before this
# migration — seeding every category with the same per-condition points it
# already had keeps behavior identical the moment this ships; the admin can
# differentiate by category afterward via the new queue UI.
CURRENT_CONDITION_POINTS = {
    "like_new": 100,
    "good": 70,
    "worn": 40,
    "damaged": 15,
}
CATEGORIES = ["clothing", "shoes", "accessories", "bags"]


def seed_points_rules(apps, schema_editor):
    PointsRule = apps.get_model('points', 'PointsRule')
    PointsRule.objects.bulk_create([
        PointsRule(id=uuid.uuid4(), category=category, condition=condition, points=points)
        for category in CATEGORIES
        for condition, points in CURRENT_CONDITION_POINTS.items()
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('points', '0005_pointsledgerentry_awarded_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='PointsRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.CharField(choices=[('clothing', 'Clothing'), ('shoes', 'Shoes'), ('accessories', 'Accessories'), ('bags', 'Bags')], max_length=20)),
                ('condition', models.CharField(choices=[('like_new', 'Like new'), ('good', 'Good'), ('worn', 'Worn'), ('damaged', 'Damaged')], max_length=20)),
                ('points', models.PositiveIntegerField()),
            ],
            options={
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
        migrations.AddConstraint(
            model_name='pointsrule',
            constraint=models.UniqueConstraint(fields=('category', 'condition'), name='unique_points_rule_per_category_condition'),
        ),
        migrations.RunPython(seed_points_rules, migrations.RunPython.noop),
    ]
