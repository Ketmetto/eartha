from rest_framework import serializers
from .models import Item, ItemPhoto, DriverAssignment


class ItemPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemPhoto
        fields = ["id", "image"]


class ItemSerializer(serializers.ModelSerializer):
    photos = ItemPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = ["id", "category", "condition", "description", "status", "photos", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class ItemAdminSerializer(ItemSerializer):
    """Adds fields only admins should see/edit in the review queue."""
    class Meta(ItemSerializer.Meta):
        fields = ItemSerializer.Meta.fields + ["user", "rejection_reason"]


class DriverAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverAssignment
        fields = ["id", "item", "driver_name", "status", "pickup_address_snapshot"]


# ---------------------------------------------------------------------------
# New serializers for admin actions
# ---------------------------------------------------------------------------

class ItemCreateWithPhotosSerializer(serializers.Serializer):
    """
    Handles item creation with photo upload validation.
    Used by the user-facing upload view.
    """
    category = serializers.ChoiceField(choices=Item.Category.choices)
    condition = serializers.ChoiceField(choices=Item.Condition.choices)
    description = serializers.CharField(required=False, allow_blank=True)
    photos = serializers.ListField(
        # Plain FileField, not ImageField: ImageField does a strict PIL
        # decode which is redundant with base.validators' size/content-type
        # checks applied in the service layer when the item is created.
        child=serializers.FileField(),
        min_length=1,
        max_length=10,
        help_text="At least one photo is required. Max 10 photos."
    )


class SubmissionDecisionSerializer(serializers.Serializer):
    """
    Admin decision: accept or reject a pending submission.
    Drives the state machine — admins cannot set status to arbitrary values.
    """
    action = serializers.ChoiceField(
        choices=["accept", "reject"],
        help_text="Accept or reject the submission."
    )
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required when action is 'reject'."
    )

    def validate(self, attrs):
        if attrs["action"] == "reject" and not attrs.get("rejection_reason"):
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting a submission."}
            )
        return attrs


class DriverDispatchSerializer(serializers.Serializer):
    """
    Admin action: assign a driver to an accepted item.
    Creates a DriverAssignment and transitions the item to DISPATCHED.
    """
    driver_name = serializers.CharField(max_length=120)
    pickup_address_snapshot = serializers.CharField(
        help_text="Snapshot of the pickup address at time of dispatch."
    )
