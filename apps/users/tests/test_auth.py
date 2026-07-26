import pytest
from rest_framework import status
from apps.users.models import User


@pytest.mark.django_db
class TestRegister:
    url = "/api/v1/auth/register/"

    def valid_payload(self, **overrides):
        payload = {
            "email": "newuser@example.com",
            "full_name": "Jane Doe",
            "password": "S3curePass!23",
            "password_confirm": "S3curePass!23",
            "agree_to_terms": True,
        }
        payload.update(overrides)
        return payload

    def test_register_creates_user(self, api_client):
        response = api_client.post(self.url, self.valid_payload(), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="newuser@example.com")
        assert user.first_name == "Jane"
        assert user.last_name == "Doe"
        assert user.check_password("S3curePass!23")
        # username was derived, never sent by the client
        assert user.username.startswith("newuser")

    def test_register_rejects_duplicate_email(self, api_client, user):
        response = api_client.post(self.url, self.valid_payload(email=user.email), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_rejects_mismatched_passwords(self, api_client):
        response = api_client.post(
            self.url, self.valid_payload(password_confirm="somethingElse!23"), format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in response.data

    def test_register_rejects_weak_password(self, api_client):
        response = api_client.post(
            self.url, self.valid_payload(password="password", password_confirm="password"), format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_register_requires_agreeing_to_terms(self, api_client):
        response = api_client.post(self.url, self.valid_payload(agree_to_terms=False), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "agree_to_terms" in response.data

    def test_two_users_with_same_email_prefix_get_unique_usernames(self, api_client):
        api_client.post(self.url, self.valid_payload(email="jane@example.com"), format="json")
        api_client.post(
            self.url,
            self.valid_payload(email="jane@othermail.com", full_name="Jane Other"),
            format="json",
        )
        usernames = set(User.objects.values_list("username", flat=True))
        assert len(usernames) == User.objects.count()


@pytest.mark.django_db
class TestLoginAndTokens:
    def test_login_returns_access_and_refresh_tokens(self, api_client, user):
        response = api_client.post(
            "/api/v1/auth/login/", {"email": user.email, "password": "testpass123"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_rejects_wrong_password(self, api_client, user):
        response = api_client.post(
            "/api/v1/auth/login/", {"email": user.email, "password": "wrong"}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_returns_new_access_token(self, api_client, user):
        login = api_client.post(
            "/api/v1/auth/login/", {"email": user.email, "password": "testpass123"}, format="json"
        )
        response = api_client.post(
            "/api/v1/auth/refresh/", {"refresh": login.data["refresh"]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data


@pytest.mark.django_db
class TestMeEndpoint:
    def test_me_requires_authentication(self, api_client):
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_current_user(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email

    def test_me_cannot_escalate_to_staff(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/v1/auth/me/", {"is_staff": True}, format="json")
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_staff is False


@pytest.mark.django_db
class TestAdminRBAC:
    """
    IsAdmin is used across apps (e.g. the submissions review queue) but
    the permission itself is a users/auth concern, so it's tested here
    against a real protected endpoint rather than in isolation.
    """

    def test_regular_user_cannot_access_admin_queue(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/submissions/admin/queue/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_user_can_access_admin_queue(self, admin_client):
        response = admin_client.get("/api/v1/submissions/admin/queue/")
        assert response.status_code == status.HTTP_200_OK
