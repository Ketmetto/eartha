from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Wraps DRF's default handler so every error response has a
    consistent shape: {"detail": ..., "code": ...}. Extend as needed."""
    response = exception_handler(exc, context)
    if response is not None:
        # A bare-string/list ValidationError (e.g. raise ValidationError("..."))
        # renders response.data as a list, not a dict — normalize it so the
        # "status_code" key can always be added below.
        if not isinstance(response.data, dict):
            response.data = {"detail": response.data}
        response.data["status_code"] = response.status_code
    return response
