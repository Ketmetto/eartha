







































"""
Shared pytest fixtures for the submissions app tests.
Place this in apps/submissions/tests/conftest.py
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.submissions.models import Item, DriverAssignment


@pytest.fixture
def user(django_user_model):
    """Create a regular user."""
    return django_user_model.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
    )


@pytest.fixture
def admin_user(django_user_model):
    """Create an admin user."""
    return django_user_model.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="testpass123",
        is_staff=True,
    )


@pytest.fixture
def photo_file():
    """Return a valid image file for testing."""
    return SimpleUploadedFile(
        "test.jpg",
        b"fake image content",
        content_type="image/jpeg",
    )


@pytest.fixture
def pending_item(user):
    """Create a pending item for testing."""
    return Item.objects.create(
        user=user,
        category=Item.Category.CLOTHING,
        condition=Item.Condition.GOOD,
        description="A test item",
        status=Item.Status.PENDING,
    )


@pytest.fixture
def accepted_item(user):
    """Create an accepted item for testing."""
    return Item.objects.create(
        user=user,
        category=Item.Category.SHOES,
        condition=Item.Condition.LIKE_NEW,
        description="An accepted item",
        status=Item.Status.ACCEPTED,
    )


@pytest.fixture
def dispatched_item(user):
    """Create a dispatched item with a driver assignment for testing."""
    item = Item.objects.create(
        user=user,
        category=Item.Category.BAGS,
        condition=Item.Condition.WORN,
        description="A dispatched item",
        status=Item.Status.DISPATCHED,
    )
    DriverAssignment.objects.create(
        item=item,
        driver_name="Test Driver",
        status=DriverAssignment.DispatchStatus.DISPATCHED,
        pickup_address_snapshot="123 Test St",
    )
    return item
