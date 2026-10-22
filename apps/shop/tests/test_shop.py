"""
Tests for apps.shop — public checkout, stock reservation, cancellation,
and the /shop/ page's coming-soon state.
"""
import io
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status

from apps.shop.models import Order, Product
from apps.shop.services import cancel_order, make_order_form_token


def _image():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="tan").save(buf, format="JPEG")
    return SimpleUploadedFile("p.jpg", buf.getvalue(), content_type="image/jpeg")


@pytest.fixture
def make_product(db, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    def _make(**kw):
        defaults = {"name": "Linen shirt", "section": "women", "price_usd": Decimal("25.00"), "stock": 1}
        defaults.update(kw)
        return Product.objects.create(image=_image(), **defaults)
    return _make


def token(age_seconds=60):
    with patch("base.form_guard.time.time", return_value=timezone.now().timestamp() - age_seconds):
        return make_order_form_token()


def payload(lines, **overrides):
    data = {
        "full_name": "Maya H.",
        "phone": "03 123 456",
        "email": "Maya@Example.com",
        "city": "Beirut",
        "address": "Hamra Street",
        "items": lines,
        "website": "",
        "form_token": token(),
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
class TestOrderCreateView:
    url = reverse("shop-order-create")

    def test_anonymous_order_reserves_stock_and_emails(self, api_client, make_product, django_capture_on_commit_callbacks):
        shirt = make_product(stock=1)
        jeans = make_product(name="Kids jeans", section="kids", price_usd=Decimal("12.50"), stock=5)

        with django_capture_on_commit_callbacks(execute=True):
            response = api_client.post(
                self.url,
                payload([{"product": str(shirt.id), "quantity": 1}, {"product": str(jeans.id), "quantity": 2}]),
                format="json",
            )

        assert response.status_code == status.HTTP_201_CREATED
        order = Order.objects.get()
        assert response.data["order"] == order.number
        assert order.total_usd == Decimal("50.00")
        assert order.phone == "+9613123456"
        assert order.email == "maya@example.com"
        assert order.items.count() == 2
        shirt.refresh_from_db(); jeans.refresh_from_db()
        assert (shirt.stock, jeans.stock) == (0, 3)
        recipients = sorted(m.to[0] for m in mail.outbox)
        assert recipients == ["info@eartha.me", "maya@example.com"]

    def test_price_comes_from_database_not_client(self, api_client, make_product):
        shirt = make_product(price_usd=Decimal("40.00"))
        data = payload([{"product": str(shirt.id), "quantity": 1}])
        data["total_usd"] = "0.01"
        api_client.post(self.url, data, format="json")
        assert Order.objects.get().total_usd == Decimal("40.00")

    def test_cannot_buy_more_than_stock(self, api_client, make_product):
        shirt = make_product(stock=1)
        api_client.post(self.url, payload([{"product": str(shirt.id), "quantity": 1}]), format="json")
        response = api_client.post(self.url, payload([{"product": str(shirt.id), "quantity": 1}]), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Linen shirt" in response.data["items"][0]
        assert Order.objects.count() == 1

    def test_unpublished_product_cannot_be_ordered(self, api_client, make_product):
        hidden = make_product(is_active=False)
        response = api_client.post(self.url, payload([{"product": str(hidden.id), "quantity": 1}]), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Order.objects.exists()

    def test_contact_and_location_are_required(self, api_client, make_product):
        shirt = make_product()
        response = api_client.post(
            self.url, payload([{"product": str(shirt.id), "quantity": 1}], phone="", city="", address=""), format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert {"phone", "city", "address"} <= set(response.data)

    def test_email_is_optional(self, api_client, make_product):
        shirt = make_product()
        response = api_client.post(self.url, payload([{"product": str(shirt.id), "quantity": 1}], email=""), format="json")
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize("trap", [{"website": "http://spam"}, {"form_token": None}])
    def test_bots_get_success_but_no_order(self, api_client, make_product, trap):
        shirt = make_product()
        overrides = {"website": "http://spam"} if "website" in trap else {"form_token": token(age_seconds=1)}
        response = api_client.post(self.url, payload([{"product": str(shirt.id), "quantity": 1}], **overrides), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert not Order.objects.exists()
        shirt.refresh_from_db()
        assert shirt.stock == 1

    def test_forged_token_is_rejected(self, api_client, make_product):
        shirt = make_product()
        response = api_client.post(self.url, payload([{"product": str(shirt.id), "quantity": 1}], form_token="forged"), format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cancel_returns_stock_once(api_client, make_product):
    shirt = make_product(stock=2)
    api_client.post(reverse("shop-order-create"), payload([{"product": str(shirt.id), "quantity": 2}]), format="json")
    order = Order.objects.get()
    cancel_order(order)
    cancel_order(order)
    shirt.refresh_from_db(); order.refresh_from_db()
    assert shirt.stock == 2
    assert order.status == Order.Status.CANCELLED


@pytest.mark.django_db
class TestShopPage:
    def test_coming_soon_when_nothing_published(self, client):
        html = client.get(reverse("web:shop")).content.decode()
        assert "Coming soon." in html
        assert "shop-products" not in html

    def test_lists_products_and_marks_empty_sections(self, client, make_product):
        make_product(name="Linen shirt", section="women")
        make_product(name="Sold piece", section="men", stock=0)
        html = client.get(reverse("web:shop")).content.decode()
        assert "Linen shirt" in html
        assert "Sold piece" not in html
        # men and kids have nothing in stock
        assert html.count("Coming soon.") == 2


# ---------------------------------------------------------------------------
# Admin API behind /shop/manage/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestShopAdminApi:

    def test_non_admins_are_forbidden(self, auth_client, api_client):
        assert auth_client.get(reverse("shop-admin-products")).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get(reverse("shop-admin-orders")).status_code in (401, 403)

    def test_create_product_with_photos(self, admin_client, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        response = admin_client.post(
            reverse("shop-admin-products"),
            {"name": "Wool coat", "section": "men", "price_usd": "60", "stock": "1",
             "is_active": "true", "photos": [_image(), _image()]},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        product = Product.objects.get()
        assert product.extra_images.count() == 1
        assert len(response.data["images"]) == 2

    def test_create_requires_a_photo(self, admin_client):
        response = admin_client.post(
            reverse("shop-admin-products"),
            {"name": "Wool coat", "section": "men", "price_usd": "60", "stock": "1"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "photos" in response.data

    def test_edit_without_photos_keeps_them_and_new_photos_replace(self, admin_client, make_product):
        product = make_product()
        url = reverse("shop-admin-product-detail", args=[product.id])
        old_image = product.image.name

        response = admin_client.patch(url, {"price_usd": "30.00", "is_active": "false"}, format="multipart")
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert (product.price_usd, product.is_active, product.image.name) == (Decimal("30.00"), False, old_image)

        admin_client.patch(url, {"photos": [_image(), _image(), _image()]}, format="multipart")
        product.refresh_from_db()
        assert product.image.name != old_image
        assert product.extra_images.count() == 2

    def test_order_flow_and_cancel_restores_stock(self, admin_client, api_client, make_product):
        product = make_product(stock=1)
        api_client.post(reverse("shop-order-create"), payload([{"product": str(product.id), "quantity": 1}]), format="json")
        order = Order.objects.get()

        assert admin_client.get(reverse("shop-admin-orders"), {"view": "open"}).data[0]["number"] == order.number
        assert admin_client.get(reverse("shop-admin-new-order-count")).data == {"new": 1}

        url = reverse("shop-admin-order-status", args=[order.id])
        assert admin_client.post(url, {"status": "confirmed"}, format="json").data["status"] == "confirmed"
        assert admin_client.post(url, {"status": "cancelled"}, format="json").data["status"] == "cancelled"
        product.refresh_from_db()
        assert product.stock == 1
        assert admin_client.get(reverse("shop-admin-orders"), {"view": "done"}).data[0]["status"] == "cancelled"

    def test_status_cannot_go_backwards(self, admin_client, api_client, make_product):
        product = make_product()
        api_client.post(reverse("shop-order-create"), payload([{"product": str(product.id), "quantity": 1}]), format="json")
        order = Order.objects.get()
        url = reverse("shop-admin-order-status", args=[order.id])
        admin_client.post(url, {"status": "confirmed"}, format="json")
        admin_client.post(url, {"status": "delivered"}, format="json")
        response = admin_client.post(url, {"status": "cancelled"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        order.refresh_from_db()
        assert order.status == Order.Status.DELIVERED


@pytest.mark.django_db
def test_manage_page_renders(client):
    assert client.get(reverse("web:shop-manage")).status_code == 200
