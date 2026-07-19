"""
Tests for apps.submissions.state_machine
"""
import pytest
from apps.submissions.models import Item
from apps.submissions.state_machine import can_transition


class TestCanTransition:
    """Test the state machine transition rules."""

    @pytest.mark.parametrize("current,target,expected", [
        # From PENDING
        (Item.Status.PENDING, Item.Status.ACCEPTED, True),
        (Item.Status.PENDING, Item.Status.REJECTED, True),
        (Item.Status.PENDING, Item.Status.DISPATCHED, False),
        (Item.Status.PENDING, Item.Status.COLLECTED, False),
        (Item.Status.PENDING, Item.Status.COMPLETED, False),
        (Item.Status.PENDING, Item.Status.PENDING, False),

        # From ACCEPTED
        (Item.Status.ACCEPTED, Item.Status.DISPATCHED, True),
        (Item.Status.ACCEPTED, Item.Status.COMPLETED, False),
        (Item.Status.ACCEPTED, Item.Status.REJECTED, False),
        (Item.Status.ACCEPTED, Item.Status.PENDING, False),

        # From DISPATCHED
        (Item.Status.DISPATCHED, Item.Status.COLLECTED, True),
        (Item.Status.DISPATCHED, Item.Status.COMPLETED, False),
        (Item.Status.DISPATCHED, Item.Status.ACCEPTED, False),

        # From COLLECTED
        (Item.Status.COLLECTED, Item.Status.COMPLETED, True),
        (Item.Status.COLLECTED, Item.Status.DISPATCHED, False),

        # Terminal states
        (Item.Status.REJECTED, Item.Status.PENDING, False),
        (Item.Status.REJECTED, Item.Status.ACCEPTED, False),
        (Item.Status.REJECTED, Item.Status.COMPLETED, False),
        (Item.Status.COMPLETED, Item.Status.PENDING, False),
        (Item.Status.COMPLETED, Item.Status.COLLECTED, False),
    ])
    def test_all_transitions(self, current, target, expected):
        assert can_transition(current, target) == expected

    def test_unknown_current_status_returns_false(self):
        assert can_transition("unknown_status", Item.Status.ACCEPTED) is False
