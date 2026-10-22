"""
Tests for apps.engagement.views and apps.engagement.admin_views
"""
import re

import pytest
from unittest.mock import patch
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.engagement.models import ContactMessage, ImpactStat, NewsletterSubscriber
from apps.points.models import Benefit


@pytest.mark.django_db
class TestContactMessageCreateView:
    url = reverse("contact-create")

    def valid_payload(self, **overrides):
        payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "subject": "Question",
            "message": "How does pickup scheduling work?",
        }
        payload.update(overrides)
        return payload

    def test_does_not_require_authentication(self, api_client):
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            response = api_client.post(self.url, self.valid_payload(), format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_creates_message_with_partner_flag(self, api_client):
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            response = api_client.post(
                self.url, self.valid_payload(is_partner_inquiry=True), format="json"
            )
        assert response.status_code == status.HTTP_201_CREATED
        message = ContactMessage.objects.get(email="jane@example.com")
        assert message.is_partner_inquiry is True
        assert message.resolved is False

    def test_defaults_to_not_a_partner_inquiry(self, api_client):
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            api_client.post(self.url, self.valid_payload(), format="json")
        message = ContactMessage.objects.get(email="jane@example.com")
        assert message.is_partner_inquiry is False

    def test_rejects_unauthenticated_submission_using_a_registered_email(self, api_client, user):
        # The form is public — nothing else stops a visitor from typing
        # someone else's real address, which would read in the admin
        # inbox as a message genuinely from that account.
        response = api_client.post(self.url, self.valid_payload(email=user.email), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not ContactMessage.objects.filter(email=user.email).exists()

    def test_rejects_case_variant_of_a_registered_email(self, api_client, user):
        response = api_client.post(
            self.url, self.valid_payload(email=user.email.upper()), format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_allows_a_user_to_message_under_their_own_email(self, auth_client, user):
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            response = auth_client.post(self.url, self.valid_payload(email=user.email), format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_rejects_a_logged_in_user_using_someone_elses_registered_email(self, auth_client, admin_user):
        # Logged in, but as a different account than the email claims —
        # still impersonation, just not an anonymous one.
        response = auth_client.post(self.url, self.valid_payload(email=admin_user.email), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unregistered_email_still_works_anonymously(self, api_client):
        # The whole point of keeping this open: partner inquiries and
        # pre-signup questions come from people who may never have an
        # account at all.
        with patch("apps.engagement.services.notify_admin_of_contact_message"):
            response = api_client.post(
                self.url, self.valid_payload(email="brand-partner@example.com"), format="json"
            )
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestImpactStatsView:
    url = reverse("impact-stats")

    def test_does_not_require_authentication(self, api_client):
        ImpactStat.objects.create(items_collected=120, co2_saved_kg=340)
        # Two benefits for the same brand should count once, and an
        # inactive benefit shouldn't count at all.
        Benefit.objects.create(brand_name="Brio Bags", discount_percent=10, points_required=100)
        Benefit.objects.create(brand_name="Brio Bags", discount_percent=20, points_required=200)
        Benefit.objects.create(brand_name="Neam's", discount_percent=15, points_required=150)
        Benefit.objects.create(brand_name="Retired Co", discount_percent=5, points_required=50, is_active=False)

        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["items_collected"] == 120
        assert response.data["co2_saved_kg"] == 340
        assert response.data["partner_brands_count"] == 2
        assert response.data["partner_brand_names"] == ["Brio Bags", "Neam's"]


@pytest.mark.django_db
class TestContactMessageAdminListView:
    url = reverse("messages-admin-list")

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_sees_all_messages(self, admin_client):
        ContactMessage.objects.create(name="A", email="a@example.com", message="hi")
        ContactMessage.objects.create(name="B", email="b@example.com", message="hey", resolved=True)

        response = admin_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2

    def test_paginates_at_20_per_page(self, admin_client):
        for _ in range(25):
            ContactMessage.objects.create(name="A", email="a@example.com", message="hi")

        first_page = admin_client.get(self.url)
        assert first_page.status_code == status.HTTP_200_OK
        assert first_page.data["count"] == 25
        assert len(first_page.data["results"]) == 20
        assert first_page.data["next"] is not None

        second_page = admin_client.get(self.url, {"page": 2})
        assert len(second_page.data["results"]) == 5
        assert second_page.data["next"] is None

    def test_resolved_filter(self, admin_client):
        ContactMessage.objects.create(name="A", email="a@example.com", message="unread")
        ContactMessage.objects.create(name="B", email="b@example.com", message="read", resolved=True)

        unread = admin_client.get(self.url, {"resolved": "false"})
        assert unread.data["count"] == 1
        assert unread.data["results"][0]["message"] == "unread"

        read = admin_client.get(self.url, {"resolved": "true"})
        assert read.data["count"] == 1
        assert read.data["results"][0]["message"] == "read"

    def test_resolved_filter_with_page_size_gives_cheap_unread_count(self, admin_client):
        ContactMessage.objects.create(name="A", email="a@example.com", message="unread")
        ContactMessage.objects.create(name="B", email="b@example.com", message="also unread")
        ContactMessage.objects.create(name="C", email="c@example.com", message="read", resolved=True)

        response = admin_client.get(self.url, {"resolved": "false", "page_size": 1})
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestContactMessageResolveView:
    def url(self, message):
        return reverse("messages-admin-resolve", kwargs={"pk": message.id})

    def test_non_admin_cannot_resolve(self, auth_client):
        message = ContactMessage.objects.create(name="A", email="a@example.com", message="hi")
        response = auth_client.post(self.url(message))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_resolve(self, admin_client):
        message = ContactMessage.objects.create(name="A", email="a@example.com", message="hi")

        response = admin_client.post(self.url(message))

        assert response.status_code == status.HTTP_200_OK
        message.refresh_from_db()
        assert message.resolved is True


@pytest.mark.django_db
class TestAdminDashboardStatsView:
    url = reverse("admin-dashboard-stats")

    def test_non_admin_cannot_access(self, auth_client):
        response = auth_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_gets_aggregate_counts(self, admin_client):
        ContactMessage.objects.create(name="A", email="a@example.com", message="hi", resolved=False)

        response = admin_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["unread_messages_count"] == 1
        assert "recent_items" in response.data


def confirmation_token_from(email_message):
    """Pull the token out of the link in a newsletter confirmation email."""
    match = re.search(r"/newsletter/confirm/\?token=(\S+)", email_message.body)
    assert match, email_message.body
    return match.group(1)


@pytest.mark.django_db
class TestNewsletterSubscribeView:
    url = reverse("newsletter-subscribe")

    def test_stores_unconfirmed_and_emails_a_confirmation_link(self, api_client):
        response = api_client.post(self.url, {"email": "Reader@Example.com "}, format="json")
        assert response.status_code == status.HTTP_200_OK
        subscriber = NewsletterSubscriber.objects.get(email="reader@example.com")
        assert subscriber.confirmed_at is None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["reader@example.com"]
        assert "/newsletter/confirm/?token=" in mail.outbox[0].body

    def test_resubmitting_unconfirmed_address_resends_the_link(self, api_client):
        api_client.post(self.url, {"email": "reader@example.com"}, format="json")
        api_client.post(self.url, {"email": "READER@example.com"}, format="json")
        assert NewsletterSubscriber.objects.count() == 1
        assert len(mail.outbox) == 2

    def test_confirmed_address_gets_same_response_and_no_email(self, api_client):
        NewsletterSubscriber.objects.create(email="reader@example.com", confirmed_at=timezone.now())
        response = api_client.post(self.url, {"email": "reader@example.com"}, format="json")
        # Same response as a fresh signup — doesn't reveal the address
        # was already on the list.
        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 0

    def test_rejects_invalid_email(self, api_client):
        response = api_client.post(self.url, {"email": "not-an-email"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not NewsletterSubscriber.objects.exists()
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestNewsletterConfirmView:
    url = reverse("newsletter-confirm")

    def subscribe(self, api_client, email="reader@example.com"):
        api_client.post(reverse("newsletter-subscribe"), {"email": email}, format="json")
        return confirmation_token_from(mail.outbox[-1])

    def test_valid_token_confirms_subscription(self, api_client):
        token = self.subscribe(api_client)
        response = api_client.get(self.url, {"token": token})
        assert response.status_code == status.HTTP_200_OK
        assert NewsletterSubscriber.objects.get(email="reader@example.com").confirmed_at is not None

    def test_confirming_twice_keeps_original_timestamp(self, api_client):
        token = self.subscribe(api_client)
        api_client.get(self.url, {"token": token})
        first = NewsletterSubscriber.objects.get().confirmed_at
        response = api_client.get(self.url, {"token": token})
        assert response.status_code == status.HTTP_200_OK
        assert NewsletterSubscriber.objects.get().confirmed_at == first

    def test_tampered_token_is_rejected(self, api_client):
        token = self.subscribe(api_client)
        response = api_client.get(self.url, {"token": token[:-2] + "xx"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert NewsletterSubscriber.objects.get().confirmed_at is None

    def test_expired_token_is_rejected(self, api_client):
        token = self.subscribe(api_client)
        with patch("apps.engagement.services.NEWSLETTER_CONFIRM_MAX_AGE", -1):
            response = api_client.get(self.url, {"token": token})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert NewsletterSubscriber.objects.get().confirmed_at is None

    def test_missing_token_is_rejected(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestWishlistRequestCreateView:
    url = reverse("wishlist-create")

    @staticmethod
    def token(age_seconds=60):
        """A form token as if the page was loaded `age_seconds` ago."""
        from apps.engagement.services import make_wishlist_form_token
        with patch("base.form_guard.time.time", return_value=timezone.now().timestamp() - age_seconds):
            return make_wishlist_form_token()

    def valid_payload(self, **overrides):
        payload = {
            "organization": "Beirut Shelter",
            "contact_name": "Rana K.",
            "email": "Rana@Shelter.org",
            "items_needed": "Winter coats for 12 children aged 6-10",
            "location": "Beirut",
            "needed_by": "2026-12-01",
            "website": "",
            "form_token": self.token(),
        }
        payload.update(overrides)
        return payload

    def test_anonymous_request_is_saved_and_admin_notified(self, api_client):
        from apps.engagement.models import WishlistRequest
        response = api_client.post(self.url, self.valid_payload(), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        req = WishlistRequest.objects.get()
        assert req.email == "rana@shelter.org"
        assert req.status == WishlistRequest.Status.NEW
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["info@eartha.me"]
        assert "Beirut Shelter" in mail.outbox[0].subject
        assert f"/admin/engagement/wishlistrequest/{req.id}/change/" in mail.outbox[0].body

    def test_honeypot_is_silently_dropped(self, api_client):
        from apps.engagement.models import WishlistRequest
        response = api_client.post(self.url, self.valid_payload(website="http://spam.example"), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert not WishlistRequest.objects.exists()
        assert not mail.outbox

    def test_too_fast_submission_is_silently_dropped(self, api_client):
        from apps.engagement.models import WishlistRequest
        response = api_client.post(self.url, self.valid_payload(form_token=self.token(age_seconds=1)), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert not WishlistRequest.objects.exists()

    @pytest.mark.parametrize("bad_token", ["forged", None])
    def test_missing_or_forged_token_is_rejected(self, api_client, bad_token):
        payload = self.valid_payload(form_token=bad_token)
        if bad_token is None:
            del payload["form_token"]
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_expired_token_is_rejected(self, api_client):
        response = api_client.post(self.url, self.valid_payload(form_token=self.token(age_seconds=2 * 86400)), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in response.data["detail"]

    def test_required_fields(self, api_client):
        response = api_client.post(self.url, self.valid_payload(organization="", items_needed=""), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert {"organization", "items_needed"} <= set(response.data)

    def test_request_page_embeds_a_valid_token(self, client):
        from apps.engagement.services import check_wishlist_form_token
        response = client.get(reverse("web:wishlist-request"))
        assert response.status_code == 200
        token = re.search(r'data-form-token="([^"]+)"', response.content.decode()).group(1)
        assert check_wishlist_form_token(token) is False  # valid, just too fresh
