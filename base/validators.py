from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE_MB = 10


def validate_image_size(file):
    if file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Image must be under {MAX_UPLOAD_SIZE_MB}MB.")


def validate_image_content_type(file):
    content_type = getattr(file, "content_type", "") or ""
    if not content_type.startswith("image/"):
        raise ValidationError("File must be an image.")
