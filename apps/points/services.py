"""
All balance-affecting operations go through here — never write to
PointsLedgerEntry directly from a view or another app.
"""
import uuid
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from .models import PointsLedgerEntry, Benefit, Redemption
from .rules import suggested_points


def get_balance(user) -> int:
    return PointsLedgerEntry.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0


def award_points_for_item(item):
    """Called by apps.submissions.services when an item is accepted."""
    points = suggested_points(item.condition)
    PointsLedgerEntry.objects.create(
        user=item.user,
        entry_type=PointsLedgerEntry.EntryType.AWARD,
        points=points,
        reference_item=item,
        note=f"Accepted: {item.category} ({item.condition})",
    )
    from notifications.tasks import notify_points_awarded
    notify_points_awarded.delay(item.user_id, points)


def reverse_points_for_item(item):
    """Called by apps.submissions.services when an ACCEPTED item is
    corrected back to REJECTED — an admin fixing a mistaken decision.
    Claws back the original award with a matching negative ledger entry.
    Raises if the user's balance can't absorb it (they've already spent
    below what this would take back) — leaves the original award and the
    item's ACCEPTED status untouched, since the caller runs this before
    saving the new status."""
    award = (
        PointsLedgerEntry.objects.filter(reference_item=item, entry_type=PointsLedgerEntry.EntryType.AWARD)
        .order_by("-created_at")
        .first()
    )
    if not award:
        return  # nothing was ever awarded (e.g. the award itself failed) — nothing to reverse

    if get_balance(item.user) < award.points:
        raise ValidationError(
            "Cannot reverse this acceptance — the user has already spent these points."
        )

    PointsLedgerEntry.objects.create(
        user=item.user,
        entry_type=PointsLedgerEntry.EntryType.ADJUSTMENT,
        points=-award.points,
        reference_item=item,
        note=f"Reversed acceptance: {item.category} ({item.condition})",
    )


@transaction.atomic
def redeem_benefit(user, benefit: Benefit) -> Redemption:
    balance = get_balance(user)
    if balance < benefit.points_required:
        raise ValidationError("Not enough points for this benefit.")

    PointsLedgerEntry.objects.create(
        user=user,
        entry_type=PointsLedgerEntry.EntryType.REDEEM,
        points=-benefit.points_required,
        note=f"Redeemed: {benefit.brand_name}",
    )

    initials = "".join(w[0] for w in benefit.brand_name.split()).upper()[:3] or "ETH"
    code = f"EARTHA-{initials}{benefit.points_required}-{uuid.uuid4().hex[:5].upper()}"

    return Redemption.objects.create(
        user=user, benefit=benefit, points_spent=benefit.points_required, code=code
    )
