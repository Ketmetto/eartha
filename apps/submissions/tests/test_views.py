"""
Tests for apps.submissions.views and apps.submissions.admin_views
"""
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from apps.submissions.models import Item

# api_client / auth_client / admin_client come from the root conftest.py

# ---------------------------------------------------------------------------
# ItemUploadView (User-facing)
# ---------------------------------------------------------------------------

class TestItemUploadView:
    """Test photo-validated item creation through the API."""

    def test_create_item_with_photos(self, auth_client):
        photo = SimpleUploadedFile(
            "test.jpg", b"fake image content", content_type="image/jpeg"
        )

        response = auth_client.post(
            reverse("submissions-list-create"),
            data={
                "category": Item.Category.CLOTHING,
                "condition": Item.Condition.GOOD,
                "description": "A nice shirt",
                "photos": [photo],
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["category"] == Item.Category.CLOTHING
        assert len(response.data["photos"]) == 1
        assert response.data["status"] == Item.Status.PENDING

    def test_create_item_without_photos_returns_400(self, auth_client):
        response = auth_client.post(
            reverse("submissions-list-create"),
            data={
                "category": Item.Category.CLOTHING,
                "condition": Item.Condition.GOOD,
                "description": "No photos",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "photos" in str(response.data)

    def test_create_item_with_multiple_photos(self, auth_client):
        photos = [
            SimpleUploadedFile(f"test{i}.jpg", b"fake", content_type="image/jpeg")
            for i in range(3)
        ]

        response = auth_client.post(
            reverse("submissions-list-create"),
            data={
                "category": Item.Category.BAGS,
                "condition": Item.Condition.WORN,
                "photos": photos,
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data["photos"]) == 3

    def test_unauthenticated_user_cannot_create(self, api_client):
        response = api_client.post(
            reverse("submissions-list-create"),
            data={"category": Item.Category.CLOTHING, "condition": Item.Condition.GOOD},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_can_list_own_submissions(self, auth_client, user, pending_item):
        other_user = user._meta.model.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="pass",
        )
        Item.objects.create(
            user=other_user,
            category=Item.Category.SHOES,
            condition=Item.Condition.LIKE_NEW,
            status=Item.Status.PENDING,
        )

        response = auth_client.get(reverse("submissions-list-create"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(pending_item.id)


# ---------------------------------------------------------------------------
# SubmissionReviewQueueView (Admin)
# ---------------------------------------------------------------------------

class TestSubmissionReviewQueueView:
    """Test admin review queue."""

    def test_admin_sees_pending_items(self, admin_client, pending_item, accepted_item):
        response = admin_client.get(reverse("submissions-admin-queue"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(pending_item.id)

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(reverse("submissions-admin-queue"))
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        )


# ---------------------------------------------------------------------------
# SubmissionDecisionView (Admin)
# ---------------------------------------------------------------------------

class TestSubmissionDecisionView:
    """Test admin decision endpoint driving the state machine."""

    def test_admin_can_accept_pending_item(self, admin_client, pending_item):
        with (
            patch("apps.submissions.services.award_points_for_item"),
            patch("apps.submissions.services.notify_submission_status_changed"),
        ):
            response = admin_client.post(
                reverse("submissions-admin-decision", kwargs={"pk": pending_item.id}),
                data={"action": "accept"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == Item.Status.ACCEPTED

    def test_admin_can_reject_pending_item(self, admin_client, pending_item):
        with patch("apps.submissions.services.notify_submission_status_changed"):
            response = admin_client.post(
                reverse("submissions-admin-decision", kwargs={"pk": pending_item.id}),
                data={"action": "reject", "rejection_reason": "Too damaged"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == Item.Status.REJECTED
            assert response.data["rejection_reason"] == "Too damaged"

    def test_reject_without_reason_returns_400(self, admin_client, pending_item):
        response = admin_client.post(
            reverse("submissions-admin-decision", kwargs={"pk": pending_item.id}),
            data={"action": "reject"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rejection_reason" in str(response.data)

    def test_invalid_action_returns_400(self, admin_client, pending_item):
        response = admin_client.post(
            reverse("submissions-admin-decision", kwargs={"pk": pending_item.id}),
            data={"action": "complete"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_bypass_state_machine(self, admin_client, pending_item):
        """
        CRITICAL: Admin cannot set status to arbitrary values.
        The endpoint only accepts 'accept' and 'reject' actions.
        """
        response = admin_client.post(
            reverse("submissions-admin-decision", kwargs={"pk": pending_item.id}),
            data={"action": "accept"},
        )
        assert response.status_code == status.HTTP_200_OK

        with patch("apps.submissions.services.notify_submission_status_changed"):
            response = admin_client.post(
                reverse("submissions-admin-decision", kwargs={"pk": pending_item.id}),
                data={"action": "accept"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot move item" in str(response.data)

    def test_non_admin_cannot_decide(self, auth_client, pending_item):
        response = auth_client.post(
            reverse("submissions-admin-decision", kwargs={"pk": pending_item.id}),
            data={"action": "accept"},
        )
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_validation_error_returns_400_not_500(self, admin_client, accepted_item):
        """
        The bug fix: DRF ValidationError must return 400, not 500.
        Try to accept an already-accepted item (invalid transition).
        """
        with patch("apps.submissions.services.notify_submission_status_changed"):
            response = admin_client.post(
                reverse("submissions-admin-decision", kwargs={"pk": accepted_item.id}),
                data={"action": "accept"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot move item" in str(response.data)


# ---------------------------------------------------------------------------
# DriverDispatchView (Admin)
# ---------------------------------------------------------------------------

class TestDriverDispatchView:
    """Test driver assignment endpoint."""

    def test_admin_can_dispatch_accepted_item(self, admin_client, accepted_item):
        with patch("apps.submissions.services.notify_submission_status_changed"):
            response = admin_client.post(
                reverse("submissions-admin-dispatch", kwargs={"pk": accepted_item.id}),
                data={
                    "driver_name": "John Doe",
                    "pickup_address_snapshot": "123 Main St, City",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        assert "Driver assigned" in response.data["detail"]

        accepted_item.refresh_from_db()
        assert accepted_item.status == Item.Status.DISPATCHED
        assert accepted_item.dispatch.driver_name == "John Doe"

    def test_cannot_dispatch_pending_item(self, admin_client, pending_item):
        response = admin_client.post(
            reverse("submissions-admin-dispatch", kwargs={"pk": pending_item.id}),
            data={
                "driver_name": "John Doe",
                "pickup_address_snapshot": "123 Main St",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot assign driver" in str(response.data)

    def test_cannot_dispatch_already_dispatched_item(self, admin_client, accepted_item):
        with patch("apps.submissions.services.notify_submission_status_changed"):
            admin_client.post(
                reverse("submissions-admin-dispatch", kwargs={"pk": accepted_item.id}),
                data={
                    "driver_name": "John Doe",
                    "pickup_address_snapshot": "123 Main St",
                },
            )

        response = admin_client.post(
            reverse("submissions-admin-dispatch", kwargs={"pk": accepted_item.id}),
            data={
                "driver_name": "Jane Doe",
                "pickup_address_snapshot": "456 Oak St",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already assigned" in str(response.data)

    def test_missing_driver_name_returns_400(self, admin_client, accepted_item):
        response = admin_client.post(
            reverse("submissions-admin-dispatch", kwargs={"pk": accepted_item.id}),
            data={"pickup_address_snapshot": "123 Main St"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "driver_name" in str(response.data)

    def test_non_admin_cannot_dispatch(self, auth_client, accepted_item):
        response = auth_client.post(
            reverse("submissions-admin-dispatch", kwargs={"pk": accepted_item.id}),
            data={
                "driver_name": "John Doe",
                "pickup_address_snapshot": "123 Main St",
            },
        )
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        )
