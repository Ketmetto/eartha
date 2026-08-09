from django.conf import settings
from django.db import models
from base.models import BaseModel
from base.validators import validate_image_size, validate_image_content_type


class Item(BaseModel):
    class Category(models.TextChoices):
        CLOTHING = "clothing", "Clothing"
        SHOES = "shoes", "Shoes"
        ACCESSORIES = "accessories", "Accessories"
        BAGS = "bags", "Bags"

    class Condition(models.TextChoices):
        LIKE_NEW = "like_new", "Like new"
        GOOD = "good", "Good"
        WORN = "worn", "Worn"
        DAMAGED = "damaged", "Damaged"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        DISPATCHED = "dispatched", "Driver dispatched"
        COLLECTED = "collected", "Collected"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    category = models.CharField(max_length=20, choices=Category.choices)
    condition = models.CharField(max_length=20, choices=Condition.choices)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    rejection_reason = models.TextField(blank=True)


class ItemPhoto(BaseModel):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(
        upload_to="submissions/",
        validators=[validate_image_size, validate_image_content_type],
    )


class Driver(BaseModel):
    """The roster admins pick from when dispatching — separate from
    DriverAssignment.driver_name, a free-text snapshot so a later
    rename/removal here doesn't rewrite history on past dispatches."""
    name = models.CharField(max_length=120)
    # Digits only, ideally with country code (e.g. 9613123456) — used as-is
    # to build wa.me links client-side, which don't tolerate spaces/dashes.
    phone_number = models.CharField(max_length=32)


class DriverAssignment(BaseModel):
    class DispatchStatus(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        DISPATCHED = "dispatched", "Dispatched"
        COLLECTED = "collected", "Collected"
        COMPLETED = "completed", "Completed"

    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name="dispatch")
    driver_name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=DispatchStatus.choices, default=DispatchStatus.ASSIGNED)
    pickup_address_snapshot = models.TextField()
