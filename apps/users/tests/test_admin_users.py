import pytest
from rest_framework import status

from apps.users.models import User


@pytest.mark.django_db
class TestUserAdminListView:
    url = "/api/v1/auth/admin/users/"

    def test_requires_admin(self, auth_client):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_lists_users_with_stats(self, admin_client, user):
        from apps.submissions.models import Item, ItemPhoto
        from apps.points.models import PointsLedgerEntry, Redemption, Benefit
        from django.core.files.uploadedfile import SimpleUploadedFile

        item = Item.objects.create(user=user, category="clothing", condition="good")
        ItemPhoto.objects.create(
            item=item, image=SimpleUploadedFile("x.jpg", b"fake", content_type="image/jpeg")
        )
        PointsLedgerEntry.objects.create(user=user, entry_type="award", points=100)
        PointsLedgerEntry.objects.create(user=user, entry_type="redeem", points=-30)
        benefit = Benefit.objects.create(
            brand_name="Test Brand", discount_percent=10, points_required=30,
        )
        Redemption.objects.create(user=user, benefit=benefit, points_spent=30, code="ABC123")

        response = admin_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        row = next(r for r in response.data["results"] if r["id"] == user.id)
        assert row["submissions_count"] == 1
        assert row["redemptions_count"] == 1
        assert row["points_balance"] == 70

    def test_search_matches_email(self, admin_client, user, admin_user):
        response = admin_client.get(self.url, {"search": user.email})
        emails = [r["email"] for r in response.data["results"]]
        assert user.email in emails
        assert admin_user.email not in emails


@pytest.mark.django_db
class TestUserBanView:
    def url(self, pk):
        return f"/api/v1/auth/admin/users/{pk}/ban/"

    def test_requires_admin(self, auth_client, user):
        response = auth_client.post(self.url(user.id), {"reason": "test"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bans_user(self, admin_client, user):
        response = admin_client.post(self.url(user.id), {"reason": "abuse"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_active is False
        assert user.ban_reason == "abuse"
        assert user.banned_at is not None

    def test_reason_is_optional(self, admin_client, user):
        response = admin_client.post(self.url(user.id), {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_active is False

    def test_admin_cannot_ban_own_account(self, admin_client, admin_user):
        response = admin_client.post(self.url(admin_user.id), {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        admin_user.refresh_from_db()
        assert admin_user.is_active is True


@pytest.mark.django_db
class TestUserUnbanView:
    def url(self, pk):
        return f"/api/v1/auth/admin/users/{pk}/unban/"

    def test_requires_admin(self, auth_client, user):
        response = auth_client.post(self.url(user.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unbans_user(self, admin_client, user):
        from apps.users import services
        services.ban_user(user, reason="abuse")

        response = admin_client.post(self.url(user.id))

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_active is True
        assert user.ban_reason == ""
        assert user.banned_at is None
