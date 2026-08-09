from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.exceptions import ValidationError
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

    def test_email_is_stored_lowercase(self, api_client):
        response = api_client.post(
            self.url, self.valid_payload(email="Mixed.Case@Example.com"), format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="mixed.case@example.com").exists()

    def test_rejects_duplicate_email_differing_only_by_case(self, api_client, user):
        # user's fixture email is test@example.com — same account, just
        # typed in a different case, is still "an account with this email"
        response = api_client.post(
            self.url, self.valid_payload(email=user.email.upper()), format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data


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

    # See apps.users.services.request_email_change for why a changed
    # email doesn't apply until confirmed.
    @patch("apps.users.services.send_transactional_email")
    def test_email_change_does_not_apply_immediately(self, mock_send, api_client, user):
        original_email = user.email
        api_client.force_authenticate(user=user)

        response = api_client.patch("/api/v1/auth/me/", {"email": "new@example.com"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == original_email
        assert response.data["pending_email"] == "new@example.com"
        user.refresh_from_db()
        assert user.email == original_email
        assert user.pending_email == "new@example.com"
        mock_send.delay.assert_called_once()
        assert mock_send.delay.call_args.kwargs["to_email"] == "new@example.com"

    @patch("apps.users.services.send_transactional_email")
    def test_email_change_rejects_address_already_in_use(self, mock_send, api_client, user, admin_user):
        api_client.force_authenticate(user=user)

        response = api_client.patch("/api/v1/auth/me/", {"email": admin_user.email}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.pending_email is None
        mock_send.delay.assert_not_called()

    def test_other_fields_roll_back_when_email_change_fails(self, api_client, user):
        # Forces request_email_change to raise mid-request (a plain
        # duplicate address is instead caught earlier, by DRF's own
        # validator — see test_rejects_if_the_email_was_claimed_by_
        # someone_else_meanwhile in test_email_change.py) and confirms
        # first_name, sent in the same request, doesn't persist anyway.
        api_client.force_authenticate(user=user)
        original_first_name = user.first_name

        with patch("apps.users.views.services.request_email_change", side_effect=ValidationError("boom")):
            response = api_client.patch(
                "/api/v1/auth/me/", {"email": "new@example.com", "first_name": "Changed"}, format="json"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.first_name == original_first_name
        assert user.pending_email is None

    @patch("apps.users.services.send_transactional_email")
    def test_resubmitting_the_same_email_is_a_no_op(self, mock_send, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.patch("/api/v1/auth/me/", {"email": user.email}, format="json")

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.pending_email is None
        mock_send.delay.assert_not_called()

    @patch("apps.users.services.send_transactional_email")
    def test_other_fields_still_save_alongside_a_pending_email_change(self, mock_send, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            "/api/v1/auth/me/", {"email": "new@example.com", "first_name": "Changed"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == "Changed"
        assert user.pending_email == "new@example.com"


@pytest.mark.django_db
class TestPhoneNumber:
    """"Same" Lebanese number in different clothing (spaces, a leading 0,
    a +961) normalizes to one canonical form — see
    apps.users.services.normalize_phone."""

    def test_phone_is_normalized_to_e164(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.patch("/api/v1/auth/me/", {"phone": "03 111 222"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == "+9613111222"

    def test_rejects_a_number_already_used_by_someone_else(self, api_client, user, admin_user):
        admin_user.phone = "+96170123456"
        admin_user.save(update_fields=["phone"])

        api_client.force_authenticate(user=user)
        response = api_client.patch(
            "/api/v1/auth/me/", {"phone": "(961) 70 123 456"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.phone is None

    def test_rejects_an_unparseable_number(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.patch("/api/v1/auth/me/", {"phone": "123"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_clearing_phone_stores_null_not_empty_string(self, api_client, user, admin_user):
        # Postgres doesn't consider two NULLs equal under a unique
        # constraint, but does consider two ''s equal — an unset phone has
        # to serialize as null, or a second user clearing theirs would
        # collide with the first.
        api_client.force_authenticate(user=user)
        response = api_client.patch("/api/v1/auth/me/", {"phone": ""}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] is None
        assert admin_user.phone is None  # unaffected, and no collision on either save


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
