"""
Tests for apps.points.services
"""
import pytest
from unittest.mock import patch
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.points.models import PointsLedgerEntry, Redemption
from apps.points.services import get_balance, get_awarded_total, set_item_award, redeem_benefit
from apps.submissions.models import Item

# dispatched_item comes from apps/points/tests/conftest.py


@pytest.mark.django_db
class TestGetBalance:
    def test_zero_when_no_entries(self, user):
        assert get_balance(user) == 0

    def test_sums_award_and_redeem_entries(self, user):
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=100)
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.REDEEM, points=-40)
        assert get_balance(user) == 60

    def test_scoped_to_the_given_user(self, user, django_user_model):
        other = django_user_model.objects.create_user(username="other", email="other@example.com", password="x")
        PointsLedgerEntry.objects.create(user=other, entry_type=PointsLedgerEntry.EntryType.AWARD, points=500)
        assert get_balance(user) == 0


@pytest.mark.django_db
class TestSetItemAward:
    def test_blocked_before_dispatch(self, user):
        pending = Item.objects.create(
            user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD, status=Item.Status.PENDING,
        )
        with pytest.raises(DRFValidationError):
            set_item_award(pending, 70, user)
        assert not PointsLedgerEntry.objects.filter(reference_item=pending).exists()

    def test_first_award_creates_award_entry_and_notifies(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded") as mock_notify:
            set_item_award(dispatched_item, 70, admin_user)

        entry = PointsLedgerEntry.objects.get(reference_item=dispatched_item)
        assert entry.entry_type == PointsLedgerEntry.EntryType.AWARD
        assert entry.points == 70
        assert entry.awarded_by == admin_user
        mock_notify.delay.assert_called_once_with(dispatched_item.user_id, 70)
        assert get_awarded_total(dispatched_item) == 70

    def test_zero_award_is_valid_and_still_counts_as_first_award(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded") as mock_notify:
            set_item_award(dispatched_item, 0, admin_user)

        entry = PointsLedgerEntry.objects.get(reference_item=dispatched_item)
        assert entry.entry_type == PointsLedgerEntry.EntryType.AWARD
        assert entry.points == 0
        mock_notify.delay.assert_called_once_with(dispatched_item.user_id, 0)
        assert get_awarded_total(dispatched_item) == 0

    def test_second_call_creates_adjustment_for_upward_delta(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded"):
            set_item_award(dispatched_item, 70, admin_user)
            set_item_award(dispatched_item, 100, admin_user)

        adjustment = PointsLedgerEntry.objects.filter(
            reference_item=dispatched_item, entry_type=PointsLedgerEntry.EntryType.ADJUSTMENT
        ).get()
        assert adjustment.points == 30
        assert get_awarded_total(dispatched_item) == 100
        assert get_balance(dispatched_item.user) == 100

    def test_second_call_creates_adjustment_for_downward_delta(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded"):
            set_item_award(dispatched_item, 70, admin_user)
            set_item_award(dispatched_item, 40, admin_user)

        adjustment = PointsLedgerEntry.objects.filter(
            reference_item=dispatched_item, entry_type=PointsLedgerEntry.EntryType.ADJUSTMENT
        ).get()
        assert adjustment.points == -30
        assert get_awarded_total(dispatched_item) == 40

    def test_blocks_downward_correction_when_already_spent(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded"):
            set_item_award(dispatched_item, 100, admin_user)
        PointsLedgerEntry.objects.create(
            user=dispatched_item.user, entry_type=PointsLedgerEntry.EntryType.REDEEM, points=-80,
        )

        with pytest.raises(DRFValidationError):
            set_item_award(dispatched_item, 20, admin_user)

        assert get_awarded_total(dispatched_item) == 100

    def test_allows_downward_correction_that_leaves_balance_nonnegative(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded"):
            set_item_award(dispatched_item, 100, admin_user)
        PointsLedgerEntry.objects.create(
            user=dispatched_item.user, entry_type=PointsLedgerEntry.EntryType.REDEEM, points=-30,
        )

        with patch("notifications.tasks.notify_points_awarded"):
            set_item_award(dispatched_item, 50, admin_user)

        assert get_balance(dispatched_item.user) == 20

    def test_no_change_raises(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded"):
            set_item_award(dispatched_item, 70, admin_user)

        with pytest.raises(DRFValidationError):
            set_item_award(dispatched_item, 70, admin_user)

    def test_correction_does_not_renotify(self, dispatched_item, admin_user):
        with patch("notifications.tasks.notify_points_awarded") as mock_notify:
            set_item_award(dispatched_item, 70, admin_user)
            set_item_award(dispatched_item, 100, admin_user)

        mock_notify.delay.assert_called_once_with(dispatched_item.user_id, 70)


@pytest.mark.django_db
class TestGetAwardedTotal:
    def test_none_when_never_awarded(self, dispatched_item):
        assert get_awarded_total(dispatched_item) is None


@pytest.mark.django_db
class TestRedeemBenefit:
    def test_redeems_when_balance_is_sufficient(self, user, benefit):
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=200)

        redemption = redeem_benefit(user, benefit)

        assert redemption.benefit == benefit
        assert redemption.points_spent == benefit.points_required
        assert redemption.code.startswith("EARTHA-")
        assert get_balance(user) == 200 - benefit.points_required

    def test_raises_when_balance_is_insufficient(self, user, benefit):
        with pytest.raises(DRFValidationError):
            redeem_benefit(user, benefit)
        assert Redemption.objects.count() == 0

    def test_each_redemption_gets_a_unique_code(self, user, benefit):
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=1000)

        first = redeem_benefit(user, benefit)
        second = redeem_benefit(user, benefit)

        assert first.code != second.code
