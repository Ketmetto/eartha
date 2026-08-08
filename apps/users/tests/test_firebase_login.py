from unittest.mock import patch

import pytest
from rest_framework import status

from allauth.account.models import EmailAddress
from apps.users.models import User

URL = "/api/v1/auth/social/firebase/"


def decoded_token(**overrides):
    token = {
        "uid": "firebase-uid-1",
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
        assert user.firebase_uid == "firebase-uid-1"

        email_address = EmailAddress.objects.get(user=user, email=user.email)
        assert email_address.verified is True

    @patch("apps.users.services.verify_firebase_token")
    def test_new_user_email_is_stored_lowercase(self, mock_verify, api_client):
        # Providers aren't guaranteed to send a lowercase email — without
        # normalizing here, this could create an account that doesn't
        # match a same-address, different-case account registered the
        # normal way (User.email's uniqueness is otherwise case-sensitive).
        mock_verify.return_value = (decoded_token(email="Google.User@Example.com"), None)

        response = api_client.post(URL, {"id_token": "fake-token"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert User.objects.filter(email="google.user@example.com").exists()

    @patch("apps.users.services.verify_firebase_token")
    def test_matches_existing_user_by_email(self, mock_verify, api_client, user):
        # First-time link: an account that registered with a password
        # before (no firebase_uid yet) signs in with Google for the first
        # time — should attach to it, not duplicate it.
        assert not user.firebase_uid
        mock_verify.return_value = (decoded_token(email=user.email), None)

        response = api_client.post(URL, {"id_token": "fake-token"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert User.objects.filter(email=user.email).count() == 1
        user.refresh_from_db()
        assert user.firebase_uid == "firebase-uid-1"

    @patch("apps.users.services.verify_firebase_token")
    def test_repeat_login_matches_by_uid_even_after_email_changed(self, mock_verify, api_client):
        # Regression test: the account's Django email field is mutable
        # (see request_email_change), but the Firebase identity backing it
        # shouldn't care — that's the whole point of matching by uid.
        # Before this fix, changing the profile email broke the link
        # entirely: the next Google login's email no longer matched any
        # user, so a second, empty account got created instead of finding
        # the real one.
        mock_verify.return_value = (decoded_token(), None)
        api_client.post(URL, {"id_token": "fake-token"}, format="json")
        created = User.objects.get(email="google.user@example.com")

        created.email = "totally-different@example.com"
        created.save()

        mock_verify.return_value = (decoded_token(), None)  # same uid, same Google email as before
        response = api_client.post(URL, {"id_token": "fake-token-2"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert User.objects.count() == 1
        created.refresh_from_db()
        assert created.email == "totally-different@example.com"

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
