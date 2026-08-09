"""
Fixtures specific to the submissions app. user/admin_user/api_client/
auth_client/admin_client come from the root conftest.py — don't redefine
them here.
"""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from apps.submissions.models import Item, DriverAssignment


@pytest.fixture
def make_image_bytes():
    """Factory, not a single value — base.validators.validate_image_content_type
    now actually decodes the upload (not just its declared Content-Type),
    so tests need real image bytes, not placeholder text pretending to be
    one."""
    def _make(fmt="JPEG"):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format=fmt)
        return buf.getvalue()
    return _make


@pytest.fixture
def photo_file(make_image_bytes):
    """A valid image upload for testing."""
    return SimpleUploadedFile(
        "test.jpg",
        make_image_bytes(),
        content_type="image/jpeg",
    )


@pytest.fixture
def pending_item(user):
    return Item.objects.create(
        user=user,
        category=Item.Category.CLOTHING,
        condition=Item.Condition.GOOD,
        description="A test item",
        status=Item.Status.PENDING,
    )


@pytest.fixture
def accepted_item(user):
    return Item.objects.create(
        user=user,
        category=Item.Category.SHOES,
        condition=Item.Condition.LIKE_NEW,
        description="An accepted item",
        status=Item.Status.ACCEPTED,
    )


@pytest.fixture
def dispatched_item(user):
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


@pytest.fixture
def collected_item(user):
    item = Item.objects.create(
        user=user,
        category=Item.Category.BAGS,
        condition=Item.Condition.WORN,
        description="A collected item",
        status=Item.Status.COLLECTED,
    )
    DriverAssignment.objects.create(
        item=item,
        driver_name="Test Driver",
        status=DriverAssignment.DispatchStatus.COLLECTED,
        pickup_address_snapshot="123 Test St",
    )
    return item


@pytest.fixture
def completed_item(user):
    item = Item.objects.create(
        user=user,
        category=Item.Category.BAGS,
        condition=Item.Condition.WORN,
        description="A completed item",
        status=Item.Status.COMPLETED,
    )
    DriverAssignment.objects.create(
        item=item,
        driver_name="Test Driver",
        status=DriverAssignment.DispatchStatus.COMPLETED,
        pickup_address_snapshot="123 Test St",
    )
    return item
