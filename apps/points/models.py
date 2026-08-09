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


class PointsRule(BaseModel):
    """Admin-configurable suggested-award table — one row per (category,
    condition) pair, read by apps.points.rules.suggested_points to
    pre-fill the award amount in the queue pipeline. Never auto-awards
    anything on its own; the admin can always type a different amount
    (see apps.points.services.set_item_award).

    category/condition are plain strings, not FK/enum-typed against
    apps.submissions.models.Item, matching PointsLedgerEntry.reference_item's
    string-referenced FK above — this app doesn't import submissions.models
    at module load time, to avoid a circular import (submissions imports
    points' set_item_award in its own services)."""
    CATEGORY_CHOICES = [
        ("clothing", "Clothing"),
        ("shoes", "Shoes"),
        ("accessories", "Accessories"),
        ("bags", "Bags"),
    ]
    CONDITION_CHOICES = [
        ("like_new", "Like new"),
        ("good", "Good"),
        ("worn", "Worn"),
        ("damaged", "Damaged"),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    points = models.PositiveIntegerField()

    class Meta(BaseModel.Meta):
        # A fresh `class Meta:` here (not subclassing BaseModel.Meta) would
        # silently drop the -created_at ordering every other model in this
        # app gets — Django doesn't merge Meta across abstract-base
        # inheritance unless the child explicitly subclasses the parent's.
        constraints = [
            models.UniqueConstraint(fields=["category", "condition"], name="unique_points_rule_per_category_condition"),
        ]


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
