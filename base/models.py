import uuid
from django.db import models


class BaseModel(models.Model):
    """Every domain model inherits this instead of models.Model directly."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Indexed because every model's default ordering (below) sorts by it.
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
