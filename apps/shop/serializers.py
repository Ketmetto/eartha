from rest_framework import serializers

from apps.users.services import normalize_phone

from .models import Order, OrderItem, Product


class OrderLineSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=20)


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderLineSerializer(many=True, allow_empty=False)
    # Spam traps, never stored — see base.form_guard and OrderCreateView.
    website = serializers.CharField(write_only=True, required=False, allow_blank=True)
    form_token = serializers.CharField(write_only=True)

    class Meta:
        model = Order
        fields = [
            "full_name", "phone", "email", "city", "address", "building",
            "floor_unit", "notes", "items", "website", "form_token",
        ]

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_items(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("Too many different items in one order.")
        return value


class ProductAdminSerializer(serializers.ModelSerializer):
    """The shop manager page's product rows and form. Photos are handled
    by ProductAdminListCreateView / ProductAdminDetailView, not here — the
    first uploaded photo becomes `image`, the rest ProductImage rows."""
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "section", "price_usd", "size", "description",
            "stock", "is_active", "display_order", "images", "created_at",
        ]
        read_only_fields = ["id", "images", "created_at"]

    def get_images(self, obj):
        return [obj.image.url] + [i.image.url for i in obj.extra_images.all()]


class OrderItemAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product_name", "unit_price_usd", "quantity"]


class OrderAdminSerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    items = OrderItemAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "number", "full_name", "phone", "email", "city", "address",
            "building", "floor_unit", "notes", "total_usd", "status",
            "admin_notes", "items", "created_at",
        ]
        read_only_fields = fields


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
