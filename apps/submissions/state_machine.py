"""
Legal status transitions for Item.status. apps.submissions.services calls
can_transition() before saving a new status so an invalid jump (e.g.
pending -> completed) fails loudly instead of silently corrupting data.
"""
from .models import Item

ALLOWED_TRANSITIONS = {
    Item.Status.PENDING: {Item.Status.ACCEPTED, Item.Status.REJECTED},
    Item.Status.ACCEPTED: {Item.Status.DISPATCHED},
    Item.Status.DISPATCHED: {Item.Status.COLLECTED},
    Item.Status.COLLECTED: {Item.Status.COMPLETED},
    Item.Status.REJECTED: set(),
    Item.Status.COMPLETED: set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())
