from unittest.mock import patch

import pytest
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.users import services

CONFIRM_URL = "/api/v1/auth/confirm-email-change/"


def link_parts(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = services.email_change_token.make_token(user)
    return uid, token


@pytest.mark.django_db
class TestRequestEmailChange:
    @patch("apps.users.services.send_transactional_email")
    def test_sets_pending_email_and_sends_confirmation(self, mock_send, user):
        services.request_email_change(user, "New@Example.com")

        user.refresh_from_db()
        assert user.email == "test@example.com"  # unchanged
        assert user.pending_email == "new@example.com"  # normalized
        mock_send.delay.assert_called_once()
        assert mock_send.delay.call_args.kwargs["to_email"] == "new@example.com"

    @patch("apps.users.services.send_transactional_email")
    def test_rejects_an_email_already_in_use(self, mock_send, user, admin_user):
        with pytest.raises(ValidationError):
            services.request_email_change(user, admin_user.email)

        user.refresh_from_db()
        assert user.pending_email is None
        mock_send.delay.assert_not_called()

    @patch("apps.users.services.send_transactional_email")
    def test_same_email_is_a_no_op(self, mock_send, user):
        services.request_email_change(user, user.email)

        user.refresh_from_db()
        assert user.pending_email is None
        mock_send.delay.assert_not_called()


@pytest.mark.django_db
class TestConfirmEmailChange:
    def test_applies_a_valid_pending_change(self, user):
        with patch("apps.users.services.send_transactional_email"):
            services.request_email_change(user, "new@example.com")
        user.refresh_from_db()
        uid, token = link_parts(user)

        success, message = services.confirm_email_change(uid, token)

        assert success is True
        user.refresh_from_db()
        assert user.email == "new@example.com"
        assert user.pending_email is None

    def test_rejects_when_nothing_pending(self, user):
        uid, token = link_parts(user)

        success, message = services.confirm_email_change(uid, token)

        assert success is False

    def test_stale_token_invalidated_by_a_newer_request(self, user):
        with patch("apps.users.services.send_transactional_email"):
            services.request_email_change(user, "first@example.com")
        user.refresh_from_db()
        uid, stale_token = link_parts(user)

        with patch("apps.users.services.send_transactional_email"):
            services.request_email_change(user, "second@example.com")
        user.refresh_from_db()

        success, message = services.confirm_email_change(uid, stale_token)

        assert success is False
        user.refresh_from_db()
        assert user.pending_email == "second@example.com"

    def test_rejects_if_the_email_was_claimed_by_someone_else_meanwhile(self, user, django_user_model):
        with patch("apps.users.services.send_transactional_email"):
            services.request_email_change(user, "claimed@example.com")
        user.refresh_from_db()
        uid, token = link_parts(user)

        django_user_model.objects.create_user(
            username="claimer", email="claimed@example.com", password="testpass123",
        )

        success, message = services.confirm_email_change(uid, token)

        assert success is False
        user.refresh_from_db()
        assert user.email == "test@example.com"


@pytest.mark.django_db
class TestConfirmEmailChangeView:
    def test_applies_change_via_the_endpoint(self, api_client, user):
        with patch("apps.users.services.send_transactional_email"):
            services.request_email_change(user, "new@example.com")
        user.refresh_from_db()
        uid, token = link_parts(user)

        response = api_client.get(CONFIRM_URL, {"uid": uid, "token": token})

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.email == "new@example.com"

    def test_missing_params_returns_400(self, api_client):
        response = api_client.get(CONFIRM_URL)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_token_returns_400(self, api_client, user):
        with patch("apps.users.services.send_transactional_email"):
            services.request_email_change(user, "new@example.com")
        user.refresh_from_db()
        uid, _ = link_parts(user)

        response = api_client.get(CONFIRM_URL, {"uid": uid, "token": "garbage-token"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
