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

    # PROTECT, not CASCADE: this is an audit ledger, and Django admin's
    # default "delete selected users" action would otherwise silently wipe
    # a user's whole points history along with the account. Deleting a
    # user with ledger history needs an explicit decision (anonymize/export
    # the entries first), not a side effect of one admin click.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="points_entries")
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
    pre-fill the award amount in the queue pipeline; never auto-awards.

    category/condition are plain strings rather than FK/enum-typed
    against apps.submissions.models.Item, to avoid importing that module
    at load time (submissions imports this app's own services)."""
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
        # Subclasses BaseModel.Meta, not a fresh class — otherwise this
        # would silently lose the -created_at ordering every other model
        # in the app gets.
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
    # PROTECT for the same reason as PointsLedgerEntry.user above — this is
    # redemption/audit history, not something that should vanish as a side
    # effect of deleting the account.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="redemptions")
    benefit = models.ForeignKey(Benefit, on_delete=models.PROTECT)
    points_spent = models.PositiveIntegerField()
    code = models.CharField(max_length=40, unique=True, editable=False)
