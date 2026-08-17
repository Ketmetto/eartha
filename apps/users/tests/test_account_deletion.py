import pytest
from rest_framework import status

from apps.users.models import Address
from apps.points.models import PointsLedgerEntry


@pytest.mark.django_db
class TestAccountDeletion:
    url = "/api/v1/auth/me/"

    def test_requires_authentication(self, api_client):
        response = api_client.delete(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymizes_and_deactivates(self, api_client, user):
        original_pk = user.pk
        api_client.force_authenticate(user=user)

        response = api_client.delete(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        user.refresh_from_db()
        assert user.pk == original_pk  # still exists, not hard-deleted
        assert user.email == f"deleted-{original_pk}@eartha.deleted"
        assert user.first_name == ""
        assert user.last_name == ""
        assert user.phone is None
        assert user.is_active is False
        assert user.ban_reason == "Account deleted by user"
        assert user.banned_at is not None

    def test_deletes_address(self, api_client, user):
        Address.objects.create(user=user, line1="12 Hamra St", city="Beirut", country="Lebanon")
        api_client.force_authenticate(user=user)

        api_client.delete(self.url)

        assert not Address.objects.filter(user=user).exists()

    def test_preserves_points_ledger_history(self, api_client, user):
        entry = PointsLedgerEntry.objects.create(
            user=user, entry_type=PointsLedgerEntry.EntryType.AWARD, points=50
        )
        api_client.force_authenticate(user=user)

        api_client.delete(self.url)

        entry.refresh_from_db()
        assert entry.user_id == user.pk

    def test_deleted_account_cannot_log_in(self, api_client, user):
        original_email = user.email
        api_client.force_authenticate(user=user)
        api_client.delete(self.url)

        response = api_client.post(
            "/api/v1/auth/login/", {"email": original_email, "password": "testpass123"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
