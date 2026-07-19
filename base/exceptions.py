from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Wraps DRF's default handler so every error response has a
    consistent shape: {"detail": ..., "code": ...}. Extend as needed."""
    response = exception_handler(exc, context)
    if response is not None:
        response.data["status_code"] = response.status_code
    return response
