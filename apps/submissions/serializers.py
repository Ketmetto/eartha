from rest_framework import serializers
from .models import Item, ItemPhoto, Driver, DriverAssignment


class ItemPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemPhoto
        fields = ["id", "image"]


class ItemSerializer(serializers.ModelSerializer):
    photos = ItemPhotoSerializer(many=True, read_only=True)
    # Real awarded amount from the points ledger — null until an admin has
    # awarded points (any time from COLLECTED onward), not a guess from
    # condition. Safe to expose to the owning user, it's their own points.
    awarded_points = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ["id", "category", "condition", "description", "status", "photos", "created_at", "awarded_points"]
        read_only_fields = ["id", "status", "created_at"]

    def get_awarded_points(self, obj):
        # List views pass a pre-computed lookup in context (one query for
        # the whole list — see get_awarded_totals) instead of one query
        # per item; falls back to the single-item query when serializing
        # just one object (e.g. after creating or awarding an item).
        totals = self.context.get("awarded_totals")
        if totals is not None:
            return totals.get(obj.id)
        from apps.points.services import get_awarded_total
        return get_awarded_total(obj)


class ItemAdminSerializer(ItemSerializer):
    """Adds fields only admins should see/edit in the review queue."""
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    pickup_address = serializers.SerializerMethodField()
    pickup_instructions = serializers.SerializerMethodField()
    pickup_latitude = serializers.SerializerMethodField()
    pickup_longitude = serializers.SerializerMethodField()
    driver_name = serializers.SerializerMethodField()

    class Meta(ItemSerializer.Meta):
        fields = ItemSerializer.Meta.fields + [
            "user", "user_name", "user_email", "user_phone", "pickup_address", "pickup_instructions",
            "pickup_latitude", "pickup_longitude", "driver_name",
            "rejection_reason", "updated_at",
        ]

    def get_user_name(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name or obj.user.email

    def get_user_email(self, obj):
        return obj.user.email

    def get_user_phone(self, obj):
        return obj.user.phone or None

    def get_pickup_address(self, obj):
        address = getattr(obj.user, "address", None)
        return address.as_pickup_text() if address else None

    def get_pickup_instructions(self, obj):
        address = getattr(obj.user, "address", None)
        return (address.instructions or None) if address else None

    # Null whenever the address predates the map pin-drop step, or the pin
    # was never confirmed — see Address.latitude's docstring. The queue
    # falls back to text-address-only dispatch messages in that case.
    def get_pickup_latitude(self, obj):
        address = getattr(obj.user, "address", None)
        return address.latitude if address else None

    def get_pickup_longitude(self, obj):
        address = getattr(obj.user, "address", None)
        return address.longitude if address else None

    def get_driver_name(self, obj):
        dispatch = getattr(obj, "dispatch", None)
        return dispatch.driver_name if dispatch else None


class DriverSerializer(serializers.ModelSerializer):
    """Admin driver roster — the dropdown on the pipeline's dispatch step
    is populated from this, not free text."""
    class Meta:
        model = Driver
        fields = ["id", "name", "phone_number"]


class DriverAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverAssignment
        fields = ["id", "item", "driver_name", "status", "pickup_address_snapshot"]


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
        required=False,
        allow_blank=True,
        help_text=(
            "Snapshot of the pickup address at time of dispatch. "
            "Optional — falls back to the user's saved address if omitted."
        ),
    )


class DriverReassignSerializer(serializers.Serializer):
    """Admin action: correct the driver on an already-dispatched item."""
    driver_name = serializers.CharField(max_length=120)
