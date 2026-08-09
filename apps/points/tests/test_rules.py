"""
Tests for apps.points.rules
"""
import pytest

from apps.points.models import PointsRule
from apps.points.rules import suggested_points


@pytest.mark.django_db
class TestSuggestedPoints:
    # The 0006_pointsrule migration seeds all 16 category/condition
    # combinations in every environment, test DBs included — start from a
    # clean slate so these tests aren't just re-asserting seed data.
    def setup_method(self):
        PointsRule.objects.all().delete()

    def test_returns_the_configured_amount(self):
        PointsRule.objects.create(category="shoes", condition="good", points=55)

        assert suggested_points("shoes", "good") == 55

    def test_different_categories_can_have_different_amounts(self):
        # The whole point of the category axis: "good shoes" and "good
        # bags" don't have to be worth the same.
        PointsRule.objects.create(category="shoes", condition="good", points=55)
        PointsRule.objects.create(category="bags", condition="good", points=90)

        assert suggested_points("shoes", "good") == 55
        assert suggested_points("bags", "good") == 90

    def test_missing_combination_defaults_to_zero(self):
        assert suggested_points("clothing", "like_new") == 0
