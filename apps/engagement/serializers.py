from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.points.models import Benefit
from .models import ContactMessage, ImpactStat


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message", "is_partner_inquiry"]

    def validate_email(self, value):
        # A registered email is only allowed through when the request is
        # actually authenticated as that account — otherwise a visitor
        # could impersonate any user in the admin inbox.
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
    # Distinct brand_name, not row count — a brand with two active benefits
    # (e.g. two discount tiers) should still count once, matching what a
    # visitor actually sees on the Benefits page. partner_brand_names backs
    # the About page's logo strip — BenefitListView (the real source for the
    # logged-in Benefits page) requires auth, and the About page is public,
    # so it needs its own live, unauthenticated source instead of the stale
    # localStorage catalog it used before.
    partner_brands_count = serializers.SerializerMethodField()
    partner_brand_names = serializers.SerializerMethodField()

    class Meta:
        model = ImpactStat
        fields = ["items_collected", "co2_saved_kg", "partner_brands_count", "partner_brand_names"]

    def get_partner_brand_names(self, obj):
        return list(
            Benefit.objects.filter(is_active=True)
            .values_list("brand_name", flat=True)
            .distinct()
            .order_by("brand_name")
        )

    def get_partner_brands_count(self, obj):
        return len(self.get_partner_brand_names(obj))
