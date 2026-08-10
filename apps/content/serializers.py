from rest_framework import serializers
from .models import SiteText, SiteImage


class SiteTextAdminSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_key_display", read_only=True)

    class Meta:
        model = SiteText
        fields = ["key", "label", "value"]
        read_only_fields = ["key", "label"]


class SiteImageAdminSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="get_key_display", read_only=True)

    class Meta:
        model = SiteImage
        fields = ["key", "label", "image"]
        read_only_fields = ["key", "label"]
