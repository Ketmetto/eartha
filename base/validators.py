import pillow_heif
from django.core.exceptions import ValidationError
from PIL import Image

# Plain Pillow can't decode HEIC/HEIF — this registers a real opener so
# verify() below works on it too, instead of giving it a free pass on
# content-type alone.
pillow_heif.register_heif_opener()

MAX_UPLOAD_SIZE_MB = 10

# SVG excluded on purpose: it can embed <script>, which runs if a
# browser is ever pointed at the file directly (uploads have no auth
# check; see nginx/nginx.conf's /media/ location). HEIC/HEIF included
# since it's the default iPhone capture format.
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


def validate_image_size(file):
    if file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Image must be under {MAX_UPLOAD_SIZE_MB}MB.")


def validate_image_content_type(file):
    # content_type only exists on a freshly-uploaded file — an
    # already-saved FieldFile has none, so re-saving a form without
    # replacing the file (e.g. admin re-validating existing photos)
    # shouldn't fail on a field that was already checked once.
    content_type = getattr(file, "content_type", None)
    if content_type is None:
        return
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError("File must be a JPEG, PNG, or WEBP image.")

    # The check above is only on what the client *claims* — decoding the
    # real bytes is the only way to know it's genuinely a photo. Broad
    # except on purpose: any decode failure should reject it, including
    # Pillow's DecompressionBombError, which isn't an OSError.
    try:
        Image.open(file).verify()
    except Exception:
        raise ValidationError("File is not a valid image.")
    finally:
        file.seek(0)  # verify() consumes the stream; rewind for the actual save
