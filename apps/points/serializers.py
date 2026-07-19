from rest_framework import serializers
from .models import PointsLedgerEntry, Benefit, Redemption


class PointsLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsLedgerEntry
        fields = ["id", "entry_type", "points", "note", "created_at"]


class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Benefit
        fields = ["id", "brand_name", "logo", "category", "discount_percent", "points_required", "display_priority"]


class RedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Redemption
        fields = ["id", "benefit", "points_spent", "created_at"]
        read_only_fields = ["points_spent", "created_at"]
