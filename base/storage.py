from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """S3-compatible storage for submission photos and benefit logos.
    Works with AWS S3 or any compatible provider (Wasabi, DO Spaces, etc.)
    via AWS_S3_ENDPOINT_URL in settings."""
    location = "media"
    file_overwrite = False
