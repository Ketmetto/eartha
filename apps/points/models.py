from django.conf import settings
from django.db import models
from base.models import BaseModel


class PointsLedgerEntry(BaseModel):
    """Append-only ledger — never mutate balance directly. Current balance
    is always sum(entries), which keeps the history auditable."""
    class EntryType(models.TextChoices):
        AWARD = "award", "Award"
        REDEEM = "redeem", "Redeem"
        ADJUSTMENT = "adjustment", "Adjustment"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="points_entries")
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    points = models.IntegerField()  # positive for award, negative for redeem
    reference_item = models.ForeignKey("submissions.Item", null=True, blank=True, on_delete=models.SET_NULL)
    # Audit only — who made the discretionary award/correction. Not used in
    # balance math, so SET_NULL is fine if the admin account is later removed.
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    note = models.CharField(max_length=255, blank=True)


class Benefit(BaseModel):
    brand_name = models.CharField(max_length=120)
    logo = models.ImageField(upload_to="benefits/", blank=True)
    category = models.CharField(max_length=50, blank=True)
    discount_percent = models.PositiveSmallIntegerField()
    points_required = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    display_priority = models.PositiveSmallIntegerField(default=0)


class Redemption(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="redemptions")
    benefit = models.ForeignKey(Benefit, on_delete=models.PROTECT)
    points_spent = models.PositiveIntegerField()
    code = models.CharField(max_length=40, unique=True, editable=False)
