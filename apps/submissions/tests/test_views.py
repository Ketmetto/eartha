"""
Tests for apps.submissions.views and apps.submissions.admin_views
"""
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from apps.submissions.models import Item, Driver

# api_client / auth_client / admin_client come from the root conftest.py

# ---------------------------------------------------------------------------
# ItemUploadView (User-facing)
# ---------------------------------------------------------------------------

class TestItemUploadView:

    def test_create_item_with_photos(self, auth_client, make_image_bytes):
        photo = SimpleUploadedFile(
            "test.jpg", make_image_bytes(), content_type="image/jpeg"
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

    def test_create_item_with_multiple_photos(self, auth_client, make_image_bytes):
        photos = [
            SimpleUploadedFile(f"test{i}.jpg", make_image_bytes(), content_type="image/jpeg")
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

    def test_rejects_svg_upload(self, auth_client):
        svg = SimpleUploadedFile(
            "test.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
            content_type="image/svg+xml",
        )

        response = auth_client.post(
            reverse("submissions-list-create"),
            data={
                "category": Item.Category.CLOTHING,
                "condition": Item.Condition.GOOD,
                "photos": [svg],
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

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
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(pending_item.id)

    def test_own_submissions_paginate_at_20_per_page(self, auth_client, user):
        for _ in range(25):
            Item.objects.create(
                user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD,
                status=Item.Status.PENDING,
            )

        first_page = auth_client.get(reverse("submissions-list-create"))
        assert first_page.data["count"] == 25
        assert len(first_page.data["results"]) == 20
        assert first_page.data["next"] is not None

        second_page = auth_client.get(reverse("submissions-list-create"), {"page": 2})
        assert len(second_page.data["results"]) == 5
        assert second_page.data["next"] is None


# ---------------------------------------------------------------------------
# SubmissionReviewQueueView (Admin)
# ---------------------------------------------------------------------------

class TestSubmissionReviewQueueView:

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
# SubmissionAdminListView / SubmissionAdminDoneListView (Admin)
# ---------------------------------------------------------------------------

class TestSubmissionAdminListView:
    """Admin action queue — pending through collected, unpaginated (see
    TestSubmissionAdminDoneListView for the completed/rejected history this
    was split from, once that list started growing unbounded)."""

    def test_returns_only_action_statuses_newest_first(
        self, admin_client, pending_item, accepted_item, dispatched_item, collected_item, completed_item, user
    ):
        rejected_item = Item.objects.create(
            user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD,
            status=Item.Status.REJECTED,
        )

        response = admin_client.get(reverse("submissions-admin-action"))

        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.data}
        assert ids == {
            str(pending_item.id), str(accepted_item.id), str(dispatched_item.id), str(collected_item.id),
        }
        assert str(completed_item.id) not in ids
        assert str(rejected_item.id) not in ids

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(reverse("submissions-admin-action"))
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)


class TestSubmissionAdminDoneListView:
    """Admin completed/rejected history — paginated since, unlike the action
    queue above, this list only ever grows."""

    def test_returns_only_done_statuses(self, admin_client, completed_item, pending_item, user):
        rejected_item = Item.objects.create(
            user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD,
            status=Item.Status.REJECTED,
        )

        response = admin_client.get(reverse("submissions-admin-done"))

        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.data["results"]}
        assert ids == {str(completed_item.id), str(rejected_item.id)}
        assert str(pending_item.id) not in ids

    def test_paginates_at_20_per_page(self, admin_client, user):
        for _ in range(25):
            Item.objects.create(
                user=user, category=Item.Category.CLOTHING, condition=Item.Condition.GOOD,
                status=Item.Status.COMPLETED,
            )

        first_page = admin_client.get(reverse("submissions-admin-done"))
        assert first_page.status_code == status.HTTP_200_OK
        assert first_page.data["count"] == 25
        assert len(first_page.data["results"]) == 20
        assert first_page.data["next"] is not None

        second_page = admin_client.get(reverse("submissions-admin-done"), {"page": 2})
        assert second_page.status_code == status.HTTP_200_OK
        assert len(second_page.data["results"]) == 5
        assert second_page.data["next"] is None

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(reverse("submissions-admin-done"))
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# SubmissionDecisionView (Admin)
# ---------------------------------------------------------------------------

class TestSubmissionDecisionView:

    def test_admin_can_accept_pending_item(self, admin_client, pending_item):
        with patch("apps.submissions.services.notify_submission_status_changed"):
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
# DriverAdminListCreateView / DriverAdminDetailView (Admin)
# ---------------------------------------------------------------------------

class TestDriverAdminViews:

    def test_admin_can_list_and_create(self, admin_client):
        Driver.objects.create(name="Existing Driver", phone_number="9613000000")

        response = admin_client.get(reverse("submissions-admin-drivers"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        response = admin_client.post(
            reverse("submissions-admin-drivers"),
            data={"name": "Karim H.", "phone_number": "9613123456"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Karim H."
        assert Driver.objects.count() == 2

    def test_admin_can_update_and_delete(self, admin_client):
        driver = Driver.objects.create(name="Karim H.", phone_number="9613123456")

        response = admin_client.patch(
            reverse("submissions-admin-driver-detail", kwargs={"pk": driver.id}),
            data={"name": "Karim Haddad"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Karim Haddad"

        response = admin_client.delete(
            reverse("submissions-admin-driver-detail", kwargs={"pk": driver.id})
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Driver.objects.filter(id=driver.id).exists()

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(reverse("submissions-admin-drivers"))
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# DriverDispatchView (Admin)
# ---------------------------------------------------------------------------

class TestDriverDispatchView:

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


# ---------------------------------------------------------------------------
# DriverReassignView (Admin)
# ---------------------------------------------------------------------------

class TestDriverReassignView:

    def test_admin_can_reassign_driver(self, admin_client, dispatched_item):
        response = admin_client.post(
            reverse("submissions-admin-reassign-driver", kwargs={"pk": dispatched_item.id}),
            data={"driver_name": "Karim Haddad"},
        )

        assert response.status_code == status.HTTP_200_OK

        dispatched_item.refresh_from_db()
        assert dispatched_item.status == Item.Status.DISPATCHED
        assert dispatched_item.dispatch.driver_name == "Karim Haddad"

    def test_cannot_reassign_on_accepted_item(self, admin_client, accepted_item):
        response = admin_client.post(
            reverse("submissions-admin-reassign-driver", kwargs={"pk": accepted_item.id}),
            data={"driver_name": "Karim Haddad"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot reassign driver" in str(response.data)

    def test_cannot_reassign_on_collected_item(self, admin_client, collected_item):
        response = admin_client.post(
            reverse("submissions-admin-reassign-driver", kwargs={"pk": collected_item.id}),
            data={"driver_name": "Karim Haddad"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_driver_name_returns_400(self, admin_client, dispatched_item):
        response = admin_client.post(
            reverse("submissions-admin-reassign-driver", kwargs={"pk": dispatched_item.id}),
            data={},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_cannot_reassign(self, auth_client, dispatched_item):
        response = auth_client.post(
            reverse("submissions-admin-reassign-driver", kwargs={"pk": dispatched_item.id}),
            data={"driver_name": "Karim Haddad"},
        )
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        )
