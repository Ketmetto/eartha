from allauth.account.models import EmailAddress
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Address, NotificationPreference
from . import services


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "pending_email", "first_name", "last_name", "phone", "is_staff"]
        # email is writable here (MeView intercepts it before save — see
        # perform_update); pending_email is set only by request_email_change.
        read_only_fields = ["id", "is_staff", "pending_email"]
        # Disables DRF's auto UniqueValidator on phone: it would run on
        # the raw input before validate_phone normalizes it, letting
        # "70123456" and "+96170123456" both pass as "unique".
        extra_kwargs = {"phone": {"validators": []}}

    def validate_phone(self, value):
        if not value:
            return None
        normalized = services.normalize_phone(value)
        already_used = User.objects.filter(phone=normalized).exclude(pk=self.instance.pk).exists()
        if already_used:
            raise serializers.ValidationError("This phone number is already associated with another account.")
        return normalized


class RegisterSerializer(serializers.ModelSerializer):
    """
    Matches the site map's register form: full name, email, password
    (+ confirm), terms checkbox. Username isn't a user-facing field —
    it's derived from the email so the frontend never has to collect it.
    """
    # No UniqueValidator — same reasoning as UserSerializer.phone above;
    # the uniqueness check happens in validate_email, after normalizing.
    email = serializers.EmailField()
    full_name = serializers.CharField(write_only=True, max_length=150)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    agree_to_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "full_name", "password", "password_confirm", "agree_to_terms"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

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
        username = services.generate_unique_username(validated_data["email"])

        user = User(
            username=username,
            email=validated_data["email"],
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()
        return user


class EmailVerifiedTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Same as the stock JWT login, but refuses to issue tokens until the
    user's email is verified. Social logins never hit this path — they
    verify via the provider instead (see services.verify_firebase_token)."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if not (self.user.verified or EmailAddress.objects.filter(user=self.user, verified=True).exists()):
            raise serializers.ValidationError(
                {"detail": "Please verify your email address before logging in."},
                code="email_not_verified",
            )
        return data


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "line1", "building", "floor_unit", "instructions",
            "city", "country", "postal_code", "latitude", "longitude",
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ["email_enabled", "sms_enabled"]


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs.pop("new_password_confirm"):
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs


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


class UserAdminSerializer(serializers.ModelSerializer):
    """Admin: the Users page listing — profile fields plus the per-user
    stats batched in by apps.users.services.get_user_stats (see
    UserStatsListMixin), not computed per-row here."""
    name = serializers.SerializerMethodField()
    submissions_count = serializers.SerializerMethodField()
    redemptions_count = serializers.SerializerMethodField()
    points_balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "name", "phone", "date_joined", "is_staff",
            "is_active", "ban_reason", "banned_at",
            "submissions_count", "redemptions_count", "points_balance",
        ]
        read_only_fields = fields

    def get_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or obj.email

    def _stats(self, obj):
        stats = self.context.get("user_stats")
        if stats is not None:
            return stats.get(obj.id, {"submissions_count": 0, "redemptions_count": 0, "points_balance": 0})
        from . import services
        return services.get_user_stats([obj])[obj.id]

    def get_submissions_count(self, obj):
        return self._stats(obj)["submissions_count"]

    def get_redemptions_count(self, obj):
        return self._stats(obj)["redemptions_count"]

    def get_points_balance(self, obj):
        return self._stats(obj)["points_balance"]


class BanUserSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
