"""
Fixtures specific to the points app. user/admin_user/api_client/
auth_client/admin_client come from the root conftest.py — don't redefine
them here.
"""
import pytest
from apps.points.models import Benefit
from apps.submissions.models import Item


@pytest.fixture
def dispatched_item(user):
    return Item.objects.create(
        user=user,
        category=Item.Category.CLOTHING,
        condition=Item.Condition.GOOD,
        status=Item.Status.DISPATCHED,
    )


@pytest.fixture
def benefit():
    return Benefit.objects.create(
        brand_name="ByEartha",
        category="fashion",
        discount_percent=20,
        points_required=100,
        is_active=True,
        display_priority=0,
    )


@pytest.fixture
def inactive_benefit():
    return Benefit.objects.create(
        brand_name="Retired Brand",
        category="beauty",  # deliberately different from `benefit`'s category, for filter tests
        discount_percent=10,
        points_required=50,
        is_active=False,
        display_priority=1,
    )
