import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.content.models import SiteText, SiteImage

# 2x2 real JPEG — a plain ImageField (via DRF's serializer) decodes the
# upload to verify it's genuinely an image, so fake bytes get rejected.
TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAACAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDxGiiitjI//9k="
)


@pytest.mark.django_db
class TestSiteTextAdmin:
    # migration 0002 seeds every SiteText/SiteImage key already — these
    # tests use those existing rows rather than creating their own.

    def test_requires_admin(self, auth_client):
        response = auth_client.get("/api/v1/content/admin/texts/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_lists_texts(self, admin_client):
        response = admin_client.get("/api/v1/content/admin/texts/")
        assert response.status_code == status.HTTP_200_OK
        keys = [row["key"] for row in response.data]
        assert "index_hero_title" in keys

    def test_replaces_value_by_key(self, admin_client):
        response = admin_client.patch(
            "/api/v1/content/admin/texts/index_hero_title/", {"value": "New title"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert SiteText.objects.get(key="index_hero_title").value == "New title"

    def test_cannot_change_the_key(self, admin_client):
        response = admin_client.patch(
            "/api/v1/content/admin/texts/index_hero_title/",
            {"key": "about_hero_title", "value": "New title"}, format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        # the key is read-only — this just updates the row addressed by
        # the URL, it doesn't rename/move it
        assert SiteText.objects.filter(key="index_hero_title").exists()
        assert not SiteText.objects.filter(key="about_hero_title", value="New title").exists()

    def test_unknown_key_404s(self, admin_client):
        response = admin_client.patch(
            "/api/v1/content/admin/texts/not_a_real_key/", {"value": "x"}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_no_create_endpoint(self, admin_client):
        response = admin_client.post(
            "/api/v1/content/admin/texts/", {"key": "index_hero_title", "value": "x"}, format="json"
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestSiteImageAdmin:
    def test_requires_admin(self, auth_client):
        response = auth_client.get("/api/v1/content/admin/images/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_lists_images(self, admin_client):
        response = admin_client.get("/api/v1/content/admin/images/")
        assert response.status_code == status.HTTP_200_OK
        keys = [row["key"] for row in response.data]
        assert "about_hero_1" in keys

    def test_replaces_image_by_key(self, admin_client):
        image = SimpleUploadedFile("x.jpg", TINY_JPEG, content_type="image/jpeg")
        response = admin_client.patch(
            "/api/v1/content/admin/images/about_hero_1/", {"image": image}, format="multipart"
        )
        assert response.status_code == status.HTTP_200_OK
        row = SiteImage.objects.get(key="about_hero_1")
        assert row.image.name

    def test_no_create_endpoint(self, admin_client):
        response = admin_client.post(
            "/api/v1/content/admin/images/", {"key": "about_hero_1"}, format="multipart"
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_clear_reverts_to_default(self, admin_client):
        image = SimpleUploadedFile("x.jpg", TINY_JPEG, content_type="image/jpeg")
        admin_client.patch("/api/v1/content/admin/images/about_hero_1/", {"image": image}, format="multipart")
        assert SiteImage.objects.get(key="about_hero_1").image

        response = admin_client.post("/api/v1/content/admin/images/about_hero_1/clear/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["image"] is None
        assert not SiteImage.objects.get(key="about_hero_1").image

    def test_clear_requires_admin(self, auth_client):
        response = auth_client.post("/api/v1/content/admin/images/about_hero_1/clear/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
