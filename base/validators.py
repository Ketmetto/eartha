from django.core.exceptions import ValidationError

MAX_UPLOAD_SIZE_MB = 10


def validate_image_size(file):
    if file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Image must be under {MAX_UPLOAD_SIZE_MB}MB.")


def validate_image_content_type(file):
    # content_type only exists on a freshly-uploaded file from the current
    # request (e.g. UploadedFile) — an already-saved FieldFile/ImageFieldFile
    # doesn't have it at all. Re-saving a form without replacing the file
    # (e.g. editing an Item's status in admin, which re-validates its
    # existing photos) must not fail just because there's nothing new to
    # check — it was already validated when it was originally uploaded.
    content_type = getattr(file, "content_type", None)
    if content_type is None:
        return
    if not content_type.startswith("image/"):
        raise ValidationError("File must be an image.")
