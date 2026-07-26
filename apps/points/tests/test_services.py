"""
Tests for apps.points.services
"""
import pytest
from unittest.mock import patch
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.points.models import PointsLedgerEntry, Redemption
from apps.points.services import get_balance, award_points_for_item, redeem_benefit
from apps.submissions.models import Item


@pytest.fixture
def item(user):
    return Item.objects.create(
        user=user,
        category=Item.Category.CLOTHING,
        condition=Item.Condition.GOOD,
        status=Item.Status.ACCEPTED,
    )


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
class TestAwardPointsForItem:
    def test_awards_points_matching_condition(self, item):
        with patch("notifications.tasks.notify_points_awarded") as mock_notify:
            award_points_for_item(item)

        entry = PointsLedgerEntry.objects.get(user=item.user)
        assert entry.entry_type == PointsLedgerEntry.EntryType.AWARD
        assert entry.points == 70  # GOOD condition, per points/rules.py's POINTS_TABLE
        assert entry.reference_item == item
        mock_notify.delay.assert_called_once_with(item.user_id, 70)

    def test_like_new_awards_more_than_worn(self, user):
        like_new = Item.objects.create(user=user, category=Item.Category.SHOES, condition=Item.Condition.LIKE_NEW)
        worn = Item.objects.create(user=user, category=Item.Category.SHOES, condition=Item.Condition.WORN)

        with patch("notifications.tasks.notify_points_awarded"):
            award_points_for_item(like_new)
            award_points_for_item(worn)

        assert get_balance(user) == 100 + 40


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
