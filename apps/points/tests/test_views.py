"""
Tests for apps.points.views and apps.points.admin_views
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.points.models import Benefit, PointsLedgerEntry

# api_client / auth_client / admin_client / benefit / inactive_benefit /
# dispatched_item come from conftest.py (root + apps/points/tests/)


@pytest.mark.django_db
class TestBalanceView:
    url = reverse("points-balance")

    def test_requires_authentication(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_current_balance(self, auth_client, user):
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=70)
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["balance"] == 70


@pytest.mark.django_db
class TestLedgerHistoryView:
    url = reverse("points-history")

    def test_requires_authentication(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_scoped_to_authenticated_user(self, auth_client, user, django_user_model):
        other = django_user_model.objects.create_user(username="other", email="other@example.com", password="x")
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=70)
        PointsLedgerEntry.objects.create(user=other, entry_type=PointsLedgerEntry.EntryType.AWARD, points=999)

        response = auth_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["points"] == 70


@pytest.mark.django_db
class TestBenefitListView:
    url = reverse("benefits-list")

    def test_requires_authentication(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_only_returns_active_benefits(self, auth_client, benefit, inactive_benefit):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert [b["id"] for b in response.data] == [str(benefit.id)]

    def test_filters_by_category(self, auth_client, benefit):
        other = Benefit.objects.create(
            brand_name="Beauty Co", category="beauty", discount_percent=10, points_required=50, is_active=True,
        )

        response = auth_client.get(self.url, {"category": "beauty"})

        assert response.status_code == status.HTTP_200_OK
        assert [b["id"] for b in response.data] == [str(other.id)]


@pytest.mark.django_db
class TestRedeemBenefitView:
    url = reverse("benefit-redeem")

    def test_requires_authentication(self, api_client, benefit):
        response = api_client.post(self.url, {"benefit": str(benefit.id)}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_redeems_with_sufficient_balance(self, auth_client, user, benefit):
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=200)

        response = auth_client.post(self.url, {"benefit": str(benefit.id)}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["code"].startswith("EARTHA-")

    def test_insufficient_balance_returns_400(self, auth_client, benefit):
        response = auth_client.post(self.url, {"benefit": str(benefit.id)}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestMyRedemptionsView:
    url = reverse("my-redemptions")

    def test_requires_authentication(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_scoped_to_authenticated_user(self, auth_client, user, benefit):
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=200)
        auth_client.post(reverse("benefit-redeem"), {"benefit": str(benefit.id)}, format="json")

        response = auth_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["brand_name"] == benefit.brand_name

    def test_paginates_at_20_per_page(self, auth_client, user, benefit):
        PointsLedgerEntry.objects.create(user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=100000)
        for _ in range(25):
            auth_client.post(reverse("benefit-redeem"), {"benefit": str(benefit.id)}, format="json")

        first_page = auth_client.get(self.url)
        assert first_page.data["count"] == 25
        assert len(first_page.data["results"]) == 20
        assert first_page.data["next"] is not None

        second_page = auth_client.get(self.url, {"page": 2})
        assert len(second_page.data["results"]) == 5
        assert second_page.data["next"] is None


@pytest.mark.django_db
class TestBenefitAdminListCreateView:
    url = reverse("benefits-admin-list-create")

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_includes_inactive_benefits(self, admin_client, benefit, inactive_benefit):
        response = admin_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_filters_by_category(self, admin_client, benefit, inactive_benefit):
        response = admin_client.get(self.url, {"category": inactive_benefit.category})
        assert [b["id"] for b in response.data] == [str(inactive_benefit.id)]

    def test_admin_can_create_benefit(self, admin_client):
        payload = {
            "brand_name": "New Brand", "category": "food",
            "discount_percent": 15, "points_required": 120, "is_active": True,
        }
        response = admin_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Benefit.objects.filter(brand_name="New Brand").exists()


@pytest.mark.django_db
class TestBenefitAdminDetailView:
    def url(self, benefit):
        return reverse("benefits-admin-detail", kwargs={"pk": benefit.id})

    def test_non_admin_cannot_access(self, auth_client, benefit):
        response = auth_client.get(self.url(benefit))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_deactivate(self, admin_client, benefit):
        response = admin_client.patch(self.url(benefit), {"is_active": False}, format="json")
        assert response.status_code == status.HTTP_200_OK
        benefit.refresh_from_db()
        assert benefit.is_active is False

    def test_admin_can_delete(self, admin_client, benefit):
        response = admin_client.delete(self.url(benefit))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Benefit.objects.filter(id=benefit.id).exists()


@pytest.mark.django_db
class TestBenefitReorderView:
    url = reverse("benefits-admin-reorder")

    def test_non_admin_cannot_access(self, auth_client, benefit):
        response = auth_client.post(self.url, {"ids": [str(benefit.id)]}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sets_display_priority_from_order(self, admin_client, benefit, inactive_benefit):
        response = admin_client.post(
            self.url, {"ids": [str(inactive_benefit.id), str(benefit.id)]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        inactive_benefit.refresh_from_db()
        benefit.refresh_from_db()
        assert inactive_benefit.display_priority == 0
        assert benefit.display_priority == 1


@pytest.mark.django_db
class TestItemAwardView:
    def url(self, item):
        return reverse("items-admin-award", kwargs={"pk": item.id})

    def test_non_admin_cannot_access(self, auth_client, dispatched_item):
        response = auth_client.post(self.url(dispatched_item), {"points": 70}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_blocked_before_dispatch(self, admin_client, user):
        from apps.submissions.models import Item

        pending = Item.objects.create(
            user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD, status=Item.Status.PENDING,
        )
        response = admin_client.post(self.url(pending), {"points": 70}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_award_on_dispatched_item(self, admin_client, dispatched_item):
        response = admin_client.post(self.url(dispatched_item), {"points": 70}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["awarded_points"] == 70

        entry = PointsLedgerEntry.objects.get(reference_item=dispatched_item)
        assert entry.entry_type == PointsLedgerEntry.EntryType.AWARD
        assert entry.awarded_by is not None

    def test_admin_can_award_on_collected_item(self, admin_client, user):
        from apps.submissions.models import Item

        collected = Item.objects.create(
            user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD, status=Item.Status.COLLECTED,
        )
        response = admin_client.post(self.url(collected), {"points": 40}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_admin_can_award_on_completed_item(self, admin_client, user):
        from apps.submissions.models import Item

        completed = Item.objects.create(
            user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD, status=Item.Status.COMPLETED,
        )
        response = admin_client.post(self.url(completed), {"points": 15}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_correction_respects_spent_guard(self, admin_client, dispatched_item):
        admin_client.post(self.url(dispatched_item), {"points": 100}, format="json")
        PointsLedgerEntry.objects.create(
            user=dispatched_item.user, entry_type=PointsLedgerEntry.EntryType.REDEEM, points=-80,
        )

        response = admin_client.post(self.url(dispatched_item), {"points": 10}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_points_returns_400(self, admin_client, dispatched_item):
        response = admin_client.post(self.url(dispatched_item), {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
