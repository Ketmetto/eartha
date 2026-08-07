"""
Legal status transitions for Item.status. apps.submissions.services calls
can_transition() before saving a new status so an invalid jump (e.g.
pending -> completed) fails loudly instead of silently corrupting data.
"""
from .models import Item

ALLOWED_TRANSITIONS = {
    Item.Status.PENDING: {Item.Status.ACCEPTED, Item.Status.REJECTED},
    # ACCEPTED -> REJECTED and REJECTED -> ACCEPTED are corrections for a
    # mistaken admin decision, allowed only this early — not once a driver's
    # been dispatched. No points implication either way: acceptance only
    # screens photos, points can't exist yet (see apps.points.services.
    # set_item_award, which only allows awarding from COLLECTED onward).
    Item.Status.ACCEPTED: {Item.Status.DISPATCHED, Item.Status.REJECTED},
    Item.Status.DISPATCHED: {Item.Status.COLLECTED},
    Item.Status.COLLECTED: {Item.Status.COMPLETED},
    Item.Status.REJECTED: {Item.Status.ACCEPTED},
    Item.Status.COMPLETED: set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())
