"""
Run with: python manage.py shell < scripts/seed_data.py
Populates enough data (users, sample submissions, benefits, an impact
stat row) that QA and frontend integration aren't working against an
empty DB.
"""
from apps.users.models import User
from apps.points.models import Benefit
from apps.engagement.models import ImpactStat

if not User.objects.filter(email="demo@eartha.co").exists():
    User.objects.create_user(username="demo", email="demo@eartha.co", password="demo1234")

if not User.objects.filter(email="admin@eartha.co").exists():
    User.objects.create_superuser(username="admin", email="admin@eartha.co", password="admin123")

Benefit.objects.get_or_create(
    brand_name="Sample Brand", discount_percent=15, points_required=200, is_active=True
)

ImpactStat.objects.get_or_create(items_collected=0, co2_saved_kg=0)

print("Seed data created.")
