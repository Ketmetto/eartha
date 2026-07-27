"""
Transition logic lives here, not in views/serializers, so it's testable
and reusable from the admin views, the API, and management commands.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django.db import transaction
from base.validators import validate_image_size, validate_image_content_type
from .models import Item, ItemPhoto, DriverAssignment
from .state_machine import can_transition
from apps.points.services import award_points_for_item, reverse_points_for_item
from notifications.tasks import notify_submission_status_changed


def transition_item_status(item: Item, target_status: str, *, reason: str = "") -> Item:
    """
    Drive an item through the state machine.
    Raises DRF ValidationError so DRF's exception handler returns 400,
    not an unhandled 500.
    """
    previous_status = item.status
    if not can_transition(previous_status, target_status):
        raise ValidationError(
            {"status": f"Cannot move item from {previous_status} to {target_status}."}
        )

    with transaction.atomic():
        # Reversing a mistaken acceptance: claw back its points before
        # touching status, so a blocked reversal (points already spent)
        # leaves the item ACCEPTED rather than half-corrected.
        if previous_status == Item.Status.ACCEPTED and target_status == Item.Status.REJECTED:
            reverse_points_for_item(item)

        item.status = target_status
        if target_status == Item.Status.REJECTED:
            item.rejection_reason = reason
        item.save(update_fields=["status", "rejection_reason", "updated_at"])

        if target_status == Item.Status.ACCEPTED:
            award_points_for_item(item)

    notify_submission_status_changed.delay(str(item.id), target_status)

    return item


def create_item_with_photos(*, user, category: str, condition: str, description: str = "", photos: list) -> Item:
    """
    Create an Item only if at least one valid photo is provided.
    All photos are saved inside the same transaction.
    Raises DRF ValidationError if no photos or photo validation fails.
    """
    if not photos:
        raise ValidationError({"photos": "At least one photo is required."})

    with transaction.atomic():
        item = Item.objects.create(
            user=user,
            category=category,
            condition=condition,
            description=description,
        )

        for photo_file in photos:
            # Model field validators don't run on .objects.create(), so
            # validate explicitly here before persisting.
            try:
                validate_image_size(photo_file)
                validate_image_content_type(photo_file)
            except DjangoValidationError as exc:
                raise ValidationError({"photos": exc.messages})
            ItemPhoto.objects.create(item=item, image=photo_file)

    return item


def assign_driver(*, item: Item, driver_name: str, pickup_address_snapshot: str = "") -> DriverAssignment:
    """
    Create a DriverAssignment for an ACCEPTED item and transition it to DISPATCHED.
    Raises DRF ValidationError if the item is not in ACCEPTED status.
    """
    if DriverAssignment.objects.filter(item=item).exists():
        raise ValidationError(
            {"item": "Driver already assigned to this item."}
        )

    if item.status != Item.Status.ACCEPTED:
        raise ValidationError(
            {"item": f"Cannot assign driver to item with status '{item.status}'. Must be 'accepted'."}
        )

    if not pickup_address_snapshot:
        address = getattr(item.user, "address", None)
        if not address:
            raise ValidationError(
                {"pickup_address_snapshot": "User has no saved pickup address."}
            )
        parts = [address.line1, address.line2, address.city, address.country, address.postal_code]
        pickup_address_snapshot = ", ".join(p for p in parts if p)

    with transaction.atomic():
        # Create the driver assignment
        assignment = DriverAssignment.objects.create(
            item=item,
            driver_name=driver_name,
            pickup_address_snapshot=pickup_address_snapshot,
        )

        # Transition the item through the state machine
        transition_item_status(item, Item.Status.DISPATCHED)

        # Update assignment status to dispatched
        assignment.status = DriverAssignment.DispatchStatus.DISPATCHED
        assignment.save(update_fields=["status", "updated_at"])

    return assignment
