from django.db import models
from base.models import BaseModel


class ContactMessage(BaseModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    is_partner_inquiry = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)


class ImpactStat(BaseModel):
    """Single row, admin-editable, powers the public 'About us' impact numbers.
    partner_brands_count isn't a field here — it's computed live from active
    Benefit rows in ImpactStatSerializer, so it can't drift from what the
    Benefits page actually shows."""
    items_collected = models.PositiveIntegerField(default=0)
    co2_saved_kg = models.PositiveIntegerField(default=0)
