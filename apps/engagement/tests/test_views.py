"""
Tests for apps.engagement.views and apps.engagement.admin_views
"""
import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status

from apps.engagement.models import ContactMessage, ImpactStat


@pytest.mark.django_db
class TestContactMessageCreateView:
    url = reverse("contact-create")

    def valid_payload(self, **overrides):
        payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "subject": "Question",
            "message": "How does pickup scheduling work?",
        }
        payload.update(overrides)
        return payload

    def test_does_not_require_authentication(self, api_client):
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            response = api_client.post(self.url, self.valid_payload(), format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_creates_message_with_partner_flag(self, api_client):
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            response = api_client.post(
                self.url, self.valid_payload(is_partner_inquiry=True), format="json"
            )
        assert response.status_code == status.HTTP_201_CREATED
        message = ContactMessage.objects.get(email="jane@example.com")
        assert message.is_partner_inquiry is True
        assert message.resolved is False

    def test_defaults_to_not_a_partner_inquiry(self, api_client):
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            api_client.post(self.url, self.valid_payload(), format="json")
        message = ContactMessage.objects.get(email="jane@example.com")
        assert message.is_partner_inquiry is False


@pytest.mark.django_db
class TestImpactStatsView:
    url = reverse("impact-stats")

    def test_does_not_require_authentication(self, api_client):
        ImpactStat.objects.create(items_collected=120, co2_saved_kg=340, partner_brands_count=8)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["items_collected"] == 120
        assert response.data["co2_saved_kg"] == 340
        assert response.data["partner_brands_count"] == 8


@pytest.mark.django_db
class TestContactMessageAdminListView:
    url = reverse("messages-admin-list")

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_sees_all_messages(self, admin_client):
        ContactMessage.objects.create(name="A", email="a@example.com", message="hi")
        ContactMessage.objects.create(name="B", email="b@example.com", message="hey", resolved=True)

        response = admin_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestContactMessageResolveView:
    def url(self, message):
        return reverse("messages-admin-resolve", kwargs={"pk": message.id})

    def test_non_admin_cannot_resolve(self, auth_client):
        message = ContactMessage.objects.create(name="A", email="a@example.com", message="hi")
        response = auth_client.post(self.url(message))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_resolve(self, admin_client):
        message = ContactMessage.objects.create(name="A", email="a@example.com", message="hi")

        response = admin_client.post(self.url(message))

        assert response.status_code == status.HTTP_200_OK
        message.refresh_from_db()
        assert message.resolved is True


@pytest.mark.django_db
class TestAdminDashboardStatsView:
    url = reverse("admin-dashboard-stats")

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_gets_aggregate_counts(self, admin_client):
        ContactMessage.objects.create(name="A", email="a@example.com", message="hi", resolved=False)

        response = admin_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["unread_messages_count"] == 1
        assert "recent_items" in response.data
