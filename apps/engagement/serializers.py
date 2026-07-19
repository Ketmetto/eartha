from rest_framework import serializers
from .models import ContactMessage, ImpactStat


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message", "is_partner_inquiry"]


class ImpactStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpactStat
        fields = ["items_collected", "co2_saved_kg", "partner_brands_count"]
