import pillow_heif
from django.core.exceptions import ValidationError
from PIL import Image

# Plain Pillow can't decode HEIC/HEIF at all — this registers a real
# opener for it, so the verify() below works uniformly across every
# allowed format instead of HEIC getting a free pass on content-type
# alone (see ALLOWED_IMAGE_CONTENT_TYPES).
pillow_heif.register_heif_opener()

MAX_UPLOAD_SIZE_MB = 10

# Deliberately narrow — these are the formats a phone/camera photo upload
# actually produces (HEIC/HEIF is the default iPhone capture format unless
# a user has "Most Compatible" enabled in Camera settings). SVG is
# excluded on purpose: it's XML, can embed <script>, and that script runs
# if a browser is ever pointed at the file directly — which anyone can
# do, since uploaded photos are served publicly with no auth check (see
# nginx/nginx.conf's /media/ location).
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
    # about a multipart upload actually requires that to match the bytes
    # that follow it. Decoding the real content is the only way to know
    # this is genuinely a photo and not, say, an SVG-with-<script> or an
    # HTML file wearing a spoofed "image/jpeg" label. Any decode failure —
    # including Pillow's own DecompressionBombError, which isn't an
    # OSError — means reject it; there's no legitimate photo upload this
    # would ever wrongly catch.
    try:
        Image.open(file).verify()
    except Exception:
        raise ValidationError("File is not a valid image.")
    finally:
        file.seek(0)  # verify() consumes the stream; rewind for the actual save
