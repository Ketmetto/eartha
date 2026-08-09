from rest_framework import serializers
from .models import PointsLedgerEntry, Benefit, PointsRule, Redemption


class PointsLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsLedgerEntry
        fields = ["id", "entry_type", "points", "note", "created_at"]


class PointsRuleSerializer(serializers.ModelSerializer):
    """The admin queue's AWARD RULES table — one row per (category,
    condition) pair. Also doubles as the input validator for
    PointsRuleBulkSaveView, which reuses this with many=True.

    validators=[] disables the UniqueTogetherValidator DRF would
    otherwise auto-generate from PointsRule's UniqueConstraint — that
    validator assumes every write is a brand-new row, but
    PointsRuleBulkSaveView's whole purpose is upserting already-existing
    (category, condition) rows, so it would reject every ordinary save
    with "this combination already exists"."""
    class Meta:
        model = PointsRule
        fields = ["category", "condition", "points"]
        validators = []


class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Benefit
        fields = ["id", "brand_name", "logo", "category", "discount_percent", "points_required", "display_priority"]


class BenefitAdminSerializer(serializers.ModelSerializer):
    """Full read/write field set — used by the admin benefits-management screen."""
    class Meta:
        model = Benefit
        fields = [
            "id", "brand_name", "logo", "category", "discount_percent",
            "points_required", "is_active", "display_priority",
        ]


class BenefitReorderSerializer(serializers.Serializer):
    """Body: {"ids": [uuid, uuid, ...]} — the new front-to-back display order."""
    ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)


class ItemAwardSerializer(serializers.Serializer):
    """Body for ItemAwardView — the exact points to set for this item
    (pre-filled client-side from suggested_points, but freely editable)."""
    points = serializers.IntegerField(min_value=0)


class RedemptionSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="benefit.brand_name", read_only=True)
    discount_percent = serializers.IntegerField(source="benefit.discount_percent", read_only=True)

    class Meta:
        model = Redemption
        fields = ["id", "benefit", "brand_name", "discount_percent", "code", "points_spent", "created_at"]
        read_only_fields = ["points_spent", "code", "created_at"]
