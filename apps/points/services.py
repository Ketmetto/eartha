"""
All balance-affecting operations go through here — never write to
PointsLedgerEntry directly from a view or another app.
"""
import uuid
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from .models import PointsLedgerEntry, Benefit, Redemption


def _lock_user(user_id):
    """Row-lock the user for the rest of this transaction. The ledger is
    append-only (balance = sum(entries)), so there's no single balance row
    to lock directly — locking the user row instead serializes concurrent
    award/redeem calls for *that user* (a read-check-write race between two
    requests would otherwise let both pass the balance check before either
    commits, e.g. two redemptions each individually affordable but not
    together). Different users' operations are unaffected and still run
    fully in parallel. Must be called inside a transaction.atomic() block,
    before the balance is read."""
    get_user_model().objects.select_for_update().get(pk=user_id)


def get_balance(user) -> int:
    return PointsLedgerEntry.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0


def get_awarded_total(item):
    """Net points currently awarded for this item (AWARD + any ADJUSTMENT
    corrections), or None if no award has ever been made — distinct from
    0, which is itself a valid award (e.g. a misrepresented item caught on
    physical inspection)."""
    has_award = PointsLedgerEntry.objects.filter(
        reference_item=item, entry_type=PointsLedgerEntry.EntryType.AWARD
    ).exists()
    if not has_award:
        return None
    return PointsLedgerEntry.objects.filter(
        reference_item=item,
        entry_type__in=[PointsLedgerEntry.EntryType.AWARD, PointsLedgerEntry.EntryType.ADJUSTMENT],
    ).aggregate(total=Sum("points"))["total"] or 0


def set_item_award(item, points: int, admin_user) -> PointsLedgerEntry:
    """
    Award or correct the points for a submission, at admin discretion, any
    time from COLLECTED status onward — never automatically on accept or
    dispatch, since neither confirms the item is actually in Eartha's
    hands yet (acceptance only screens photos; dispatch just means a
    driver's been assigned, not that pickup happened — that could still
    fall through). First call creates an AWARD entry; a later call creates
    an ADJUSTMENT for the delta, keeping the ledger append-only. Raises if
    a downward correction would take the user's balance negative (they've
    already spent some of what this item contributed).
    """
    from apps.submissions.models import Item

    with transaction.atomic():
        _lock_user(item.user_id)
        # Refreshed after the lock, not the possibly-stale status the
        # caller already had in memory — nothing currently mutates an
        # item's status concurrently with an award call, but checking a
        # value read before the lock defeats the point of taking it.
        item.refresh_from_db(fields=["status"])

        if item.status not in (Item.Status.COLLECTED, Item.Status.COMPLETED):
            raise ValidationError(
                f"Cannot award points while item status is '{item.status}'. "
                "Item must be collected or completed."
            )

        current_total = get_awarded_total(item)
        is_first_award = current_total is None
        delta = points - (current_total or 0)

        if not is_first_award and delta == 0:
            raise ValidationError("No change — item already has this many points awarded.")

        if delta < 0 and get_balance(item.user) + delta < 0:
            raise ValidationError("Cannot reduce this award — the user has already spent these points.")

        entry = PointsLedgerEntry.objects.create(
            user=item.user,
            entry_type=PointsLedgerEntry.EntryType.AWARD if is_first_award else PointsLedgerEntry.EntryType.ADJUSTMENT,
            points=delta,
            reference_item=item,
            awarded_by=admin_user,
            note=(
                f"Awarded: {item.category} ({item.condition})" if is_first_award
                else f"Correction: {item.category} ({item.condition})"
            ),
        )

    if is_first_award:
        from notifications.tasks import notify_points_awarded
        notify_points_awarded.delay(item.user_id, points)

    return entry


@transaction.atomic
def redeem_benefit(user, benefit: Benefit) -> Redemption:
    _lock_user(user.id)

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
