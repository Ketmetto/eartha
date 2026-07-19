import uuid

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import User, Address, NotificationPreference


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone", "is_staff"]
        read_only_fields = ["id", "is_staff"]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Matches the site map's register form: full name, email, password
    (+ confirm), terms checkbox. Username isn't a user-facing field —
    it's derived from the email so the frontend never has to collect it.
    """
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="An account with this email already exists.")]
    )
    full_name = serializers.CharField(write_only=True, max_length=150)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    agree_to_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "full_name", "password", "password_confirm", "agree_to_terms"]

    def validate_agree_to_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must agree to the Terms & Privacy Policy.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("agree_to_terms")
        full_name = validated_data.pop("full_name").strip()
        password = validated_data.pop("password")

        first_name, _, last_name = full_name.partition(" ")
        username = self._generate_username(validated_data["email"])

        user = User(
            username=username,
            email=validated_data["email"],
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def _generate_username(email: str) -> str:
        base = email.split("@")[0]
        username = base
        while User.objects.filter(username=username).exists():
            username = f"{base}-{uuid.uuid4().hex[:6]}"
        return username


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["line1", "line2", "city", "country", "postal_code"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["email_enabled", "sms_enabled"]


class ChangePasswordSerializer(serializers.Serializer):
    """Not a ModelSerializer — this never reads or writes model fields
    directly, it's pure validation logic that a view hands off to
    services.change_password()."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs.pop("new_password_confirm"):
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs
