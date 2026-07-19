"""
Tests for apps.submissions.services
"""
import pytest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.submissions.models import Item, ItemPhoto, DriverAssignment
from apps.submissions.services import (
    transition_item_status,
    create_item_with_photos,
    assign_driver,
)


@pytest.fixture
def pending_item(user):
    return Item.objects.create(
        user=user,
        category=Item.Category.CLOTHING,
        condition=Item.Condition.GOOD,
        description="Test item",
        status=Item.Status.PENDING,
    )


@pytest.fixture
def accepted_item(user):
    return Item.objects.create(
        user=user,
        category=Item.Category.SHOES,
        condition=Item.Condition.LIKE_NEW,
        description="Accepted item",
        status=Item.Status.ACCEPTED,
    )


# ---------------------------------------------------------------------------
# transition_item_status
# ---------------------------------------------------------------------------

class TestTransitionItemStatus:
    """Test the state machine transition logic."""

    def test_pending_to_accepted(self, pending_item):
        with patch("apps.submissions.services.award_points_for_item") as mock_award,              patch("apps.submissions.services.notify_submission_status_changed") as mock_notify:

            result = transition_item_status(pending_item, Item.Status.ACCEPTED)

            assert result.status == Item.Status.ACCEPTED
            mock_award.assert_called_once_with(pending_item)
            mock_notify.delay.assert_called_once_with(
                str(pending_item.id), Item.Status.ACCEPTED
            )

    def test_pending_to_rejected_with_reason(self, pending_item):
        with patch("apps.submissions.services.notify_submission_status_changed") as mock_notify:
            result = transition_item_status(
                pending_item, Item.Status.REJECTED, reason="Too worn"
            )

            assert result.status == Item.Status.REJECTED
            assert result.rejection_reason == "Too worn"
            mock_notify.delay.assert_called_once_with(
                str(pending_item.id), Item.Status.REJECTED
            )

    def test_pending_to_rejected_without_reason(self, pending_item):
        with patch("apps.submissions.services.notify_submission_status_changed"):
            result = transition_item_status(pending_item, Item.Status.REJECTED)
            assert result.rejection_reason == ""

    def test_invalid_transition_raises_drf_validation_error(self, pending_item):
        """
        The key bug fix: must raise DRF ValidationError (caught by DRF -> 400),
        not Django ValidationError (uncaught -> 500).
        """
        with pytest.raises(DRFValidationError) as exc_info:
            transition_item_status(pending_item, Item.Status.COMPLETED)

        assert "Cannot move item" in str(exc_info.value.detail)
        assert pending_item.status == Item.Status.PENDING  # unchanged

    def test_accepted_to_dispatched(self, accepted_item):
        with patch("apps.submissions.services.notify_submission_status_changed") as mock_notify:
            result = transition_item_status(accepted_item, Item.Status.DISPATCHED)
            assert result.status == Item.Status.DISPATCHED
            mock_notify.delay.assert_called_once()

    def test_no_transition_from_rejected(self, user):
        rejected = Item.objects.create(
            user=user,
            category=Item.Category.BAGS,
            condition=Item.Condition.DAMAGED,
            status=Item.Status.REJECTED,
        )
        with pytest.raises(DRFValidationError):
            transition_item_status(rejected, Item.Status.ACCEPTED)

    def test_no_transition_from_completed(self, user):
        completed = Item.objects.create(
            user=user,
            category=Item.Category.ACCESSORIES,
            condition=Item.Condition.GOOD,
            status=Item.Status.COMPLETED,
        )
        with pytest.raises(DRFValidationError):
            transition_item_status(completed, Item.Status.DISPATCHED)


# ---------------------------------------------------------------------------
# create_item_with_photos
# ---------------------------------------------------------------------------

class TestCreateItemWithPhotos:
    """Test photo-validated item creation."""

    def test_creates_item_with_single_photo(self, user):
        photo = SimpleUploadedFile(
            "test.jpg", b"fake image content", content_type="image/jpeg"
        )

        item = create_item_with_photos(
            user=user,
            category=Item.Category.CLOTHING,
            condition=Item.Condition.GOOD,
            description="With photo",
            photos=[photo],
        )

        assert item.id is not None
        assert item.user == user
        assert item.photos.count() == 1
        assert item.status == Item.Status.PENDING

    def test_creates_item_with_multiple_photos(self, user):
        photos = [
            SimpleUploadedFile(f"test{i}.jpg", b"fake", content_type="image/jpeg")
            for i in range(3)
        ]

        item = create_item_with_photos(
            user=user,
            category=Item.Category.SHOES,
            condition=Item.Condition.LIKE_NEW,
            photos=photos,
        )

        assert item.photos.count() == 3

    def test_raises_when_no_photos_provided(self, user):
        with pytest.raises(DRFValidationError) as exc_info:
            create_item_with_photos(
                user=user,
                category=Item.Category.BAGS,
                condition=Item.Condition.WORN,
                photos=[],
            )

        assert "photos" in exc_info.value.detail
        assert Item.objects.filter(user=user).count() == 0  # no orphan item

    def test_transaction_rollback_on_photo_failure(self, user):
        """If photo creation fails, item should not be created."""
        bad_photo = SimpleUploadedFile(
            "test.txt", b"not an image", content_type="text/plain"
        )

        with pytest.raises(Exception):
            create_item_with_photos(
                user=user,
                category=Item.Category.CLOTHING,
                condition=Item.Condition.GOOD,
                photos=[bad_photo],
            )

        assert Item.objects.filter(user=user).count() == 0


# ---------------------------------------------------------------------------
# assign_driver
# ---------------------------------------------------------------------------

class TestAssignDriver:
    """Test driver assignment and dispatch transition."""

    def test_creates_assignment_and_transitions_to_dispatched(self, accepted_item):
        assignment = assign_driver(
            item=accepted_item,
            driver_name="John Doe",
            pickup_address_snapshot="123 Main St, City",
        )

        assert assignment.item == accepted_item
        assert assignment.driver_name == "John Doe"
        assert assignment.pickup_address_snapshot == "123 Main St, City"
        assert assignment.status == DriverAssignment.DispatchStatus.DISPATCHED

        accepted_item.refresh_from_db()
        assert accepted_item.status == Item.Status.DISPATCHED

    def test_raises_if_item_not_accepted(self, pending_item):
        with pytest.raises(DRFValidationError) as exc_info:
            assign_driver(
                item=pending_item,
                driver_name="John Doe",
                pickup_address_snapshot="123 Main St",
            )

        assert "Cannot assign driver" in str(exc_info.value.detail)

    def test_raises_if_driver_already_assigned(self, accepted_item):
        assign_driver(
            item=accepted_item,
            driver_name="John Doe",
            pickup_address_snapshot="123 Main St",
        )

        with pytest.raises(DRFValidationError) as exc_info:
            assign_driver(
                item=accepted_item,
                driver_name="Jane Doe",
                pickup_address_snapshot="456 Oak St",
            )

        assert "already assigned" in str(exc_info.value.detail)
