import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    from apps.users.models import User
    return User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
