from rest_framework import serializers
from .models import ContactMessage, ImpactStat


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message", "is_partner_inquiry"]


class ContactMessageAdminSerializer(serializers.ModelSerializer):
    """Admin inbox view — `resolved` doubles as the read/unread flag."""
    class Meta:
        model = ContactMessage
        fields = [
            "id", "name", "email", "subject", "message",
            "is_partner_inquiry", "resolved", "created_at",
        ]
        read_only_fields = ["name", "email", "subject", "message", "is_partner_inquiry", "created_at"]


class ImpactStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpactStat
        fields = ["items_collected", "co2_saved_kg", "partner_brands_count"]
