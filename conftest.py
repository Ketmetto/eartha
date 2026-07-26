"""
Shared fixtures for every app's test suite. App-specific fixtures (e.g.
submissions' pending_item) belong in that app's own tests/conftest.py —
only put something here if more than one app's tests need it.
"""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    """A regular, email-verified user. Verified so login-flow tests don't
    have to know about email verification just to authenticate."""
    from apps.users.models import User
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123", verified=True,
    )


@pytest.fixture
def admin_user(db):
    """A staff, email-verified user — for IsAdmin-gated endpoints."""
    from apps.users.models import User
    return User.objects.create_user(
        username="adminuser", email="admin@example.com", password="testpass123",
        verified=True, is_staff=True,
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
