import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAddress:
    url = "/api/v1/auth/me/address/"

    def test_requires_authentication(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_auto_creates_blank_address_for_new_user(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["line1"] == ""

    def test_update_address(self, api_client, user):
        api_client.force_authenticate(user=user)
        payload = {"line1": "12 Hamra St", "city": "Beirut", "country": "Lebanon", "postal_code": "1103"}
        response = api_client.put(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["city"] == "Beirut"

    def test_update_address_with_optional_fields(self, api_client, user):
        api_client.force_authenticate(user=user)
        payload = {
            "line1": "12 Hamra St", "city": "Beirut", "country": "Lebanon",
            "building": "Sakr Building", "floor_unit": "4th floor, Apt 12",
            "instructions": "Gate code 1234, call on arrival",
        }
        response = api_client.put(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["building"] == "Sakr Building"
        assert response.data["floor_unit"] == "4th floor, Apt 12"
        assert response.data["instructions"] == "Gate code 1234, call on arrival"

    def test_address_optional_fields_default_blank(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["building"] == ""
        assert response.data["floor_unit"] == ""
        assert response.data["instructions"] == ""

    def test_address_is_scoped_to_the_authenticated_user(self, api_client, user, django_user_model):
        other = django_user_model.objects.create_user(
            username="other", email="other@example.com", password="testpass123"
        )
        api_client.force_authenticate(user=user)
        api_client.put(self.url, {"line1": "User's address", "city": "Beirut", "country": "Lebanon"}, format="json")

        api_client.force_authenticate(user=other)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["line1"] == ""  # other's own (blank) address, not user's


@pytest.mark.django_db
class TestNotificationPreferences:
    url = "/api/v1/auth/me/notifications/"

    def test_get_auto_creates_defaults(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"email_enabled": True, "sms_enabled": False}

    def test_update_preferences(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.patch(self.url, {"sms_enabled": True}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["sms_enabled"] is True
        assert response.data["email_enabled"] is True  # untouched


@pytest.mark.django_db
class TestChangePassword:
    url = "/api/v1/auth/me/change-password/"

    def test_requires_authentication(self, api_client):
        response = api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_old_password_rejected(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            self.url,
            {"old_password": "wrong", "new_password": "N3wSecure!23", "new_password_confirm": "N3wSecure!23"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "old_password" in response.data

    def test_mismatched_new_passwords_rejected(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            self.url,
            {"old_password": "testpass123", "new_password": "N3wSecure!23", "new_password_confirm": "different"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password_confirm" in response.data

    def test_weak_new_password_rejected(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            self.url,
            {"old_password": "testpass123", "new_password": "password", "new_password_confirm": "password"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in response.data

    def test_successful_change_allows_login_with_new_password(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            self.url,
            {"old_password": "testpass123", "new_password": "N3wSecure!23", "new_password_confirm": "N3wSecure!23"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        api_client.force_authenticate(user=None)
        login = api_client.post(
            "/api/v1/auth/login/", {"email": user.email, "password": "N3wSecure!23"}, format="json"
        )
        assert login.status_code == status.HTTP_200_OK
