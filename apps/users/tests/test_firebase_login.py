from unittest.mock import patch

import pytest
from rest_framework import status

from allauth.account.models import EmailAddress
from apps.users.models import User

URL = "/api/v1/auth/social/firebase/"


def decoded_token(**overrides):
    token = {
        "email": "google.user@example.com",
        "email_verified": True,
        "name": "Google User",
    }
    token.update(overrides)
    return token


@pytest.mark.django_db
class TestFirebaseSocialLogin:
    @patch("apps.users.services.verify_firebase_token")
    def test_creates_new_user_and_returns_tokens(self, mock_verify, api_client):
        mock_verify.return_value = (decoded_token(), None)

        response = api_client.post(URL, {"id_token": "fake-token"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

        user = User.objects.get(email="google.user@example.com")
        assert user.first_name == "Google"
        assert user.last_name == "User"
        assert not user.has_usable_password()

        email_address = EmailAddress.objects.get(user=user, email=user.email)
        assert email_address.verified is True

    @patch("apps.users.services.verify_firebase_token")
    def test_matches_existing_user_by_email(self, mock_verify, api_client, user):
        mock_verify.return_value = (decoded_token(email=user.email), None)

        response = api_client.post(URL, {"id_token": "fake-token"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert User.objects.filter(email=user.email).count() == 1

    @patch("apps.users.services.verify_firebase_token")
    def test_falls_back_to_display_name_when_token_has_no_name(self, mock_verify, api_client):
        # Apple's ID token typically carries no "name" claim at all.
        mock_verify.return_value = (
            decoded_token(email="apple.user@example.com", name=None),
            None,
        )

        response = api_client.post(
            URL, {"id_token": "fake-token", "display_name": "Apple User"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        user = User.objects.get(email="apple.user@example.com")
        assert user.first_name == "Apple"
        assert user.last_name == "User"

    @patch("apps.users.services.verify_firebase_token")
    def test_rejects_invalid_token(self, mock_verify, api_client):
        mock_verify.return_value = (None, "Invalid or expired sign-in token.")

        response = api_client.post(URL, {"id_token": "bad-token"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestEmailVerifiedSurvivesProfileEdits:
    """Regression test for the sync_email_address signal: verifying an email
    (as Firebase login does) must not get silently undone by a later,
    unrelated profile save."""

    @patch("apps.users.services.verify_firebase_token")
    def test_verified_flag_survives_a_me_patch(self, mock_verify, api_client):
        mock_verify.return_value = (decoded_token(), None)
        api_client.post(URL, {"id_token": "fake-token"}, format="json")
        created_user = User.objects.get(email="google.user@example.com")

        api_client.force_authenticate(user=created_user)
        response = api_client.patch("/api/v1/auth/me/", {"first_name": "Changed"}, format="json")
        assert response.status_code == status.HTTP_200_OK

        email_address = EmailAddress.objects.get(user=created_user, email=created_user.email)
        assert email_address.verified is True
