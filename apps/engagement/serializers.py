from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ContactMessage, ImpactStat


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message", "is_partner_inquiry"]

    def validate_email(self, value):
        # The form is public and unauthenticated, so nothing normally
        # stops a visitor from typing someone else's address — the admin
        # inbox shows whatever's submitted as the sender, so that would
        # read as a message genuinely from that account. Registered
        # emails are only allowed through when the request really is
        # authenticated as that account (a logged-in user's own address).
        value = value.strip().lower()
        User = get_user_model()
        owner = User.objects.filter(email=value).first()
        request = self.context.get("request")
        is_the_owner = (
            owner and request and request.user.is_authenticated and request.user.pk == owner.pk
        )
        if owner and not is_the_owner:
            raise serializers.ValidationError(
                "This email belongs to a registered account. Sign in to contact us using it."
            )
        return value


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
