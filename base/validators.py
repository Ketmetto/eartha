import pillow_heif
from django.core.exceptions import ValidationError
from PIL import Image

# Plain Pillow can't decode HEIC/HEIF — this registers a real opener so
# verify() below works on it too, instead of giving it a free pass on
# content-type alone.
pillow_heif.register_heif_opener()

MAX_UPLOAD_SIZE_MB = 10

# What a phone/camera upload actually produces (HEIC/HEIF is the default
# iPhone capture format unless "Most Compatible" is on). SVG is excluded
# on purpose — it's XML, can embed <script>, and that runs if a browser
# is ever pointed at the file directly (uploads are served with no auth
# check; see nginx/nginx.conf's /media/ location).
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


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
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError("File must be a JPEG, PNG, or WEBP image.")

    # The check above is on the Content-Type the client *claims* — nothing
    # requires it to match the bytes that follow. Decoding the real
    # content is the only way to know this is genuinely a photo and not,
    # say, an HTML file wearing a spoofed "image/jpeg" label. Broad except:
    # any decode failure means reject it, including Pillow's
    # DecompressionBombError, which isn't an OSError.
    try:
        Image.open(file).verify()
    except Exception:
        raise ValidationError("File is not a valid image.")
    finally:
        file.seek(0)  # verify() consumes the stream; rewind for the actual save
