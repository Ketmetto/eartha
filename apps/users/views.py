from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    AddressSerializer,
    NotificationPreferenceSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerifiedTokenObtainPairSerializer,
)
from .throttles import LoginAccountRateThrottle
from . import services


class EmailVerifiedTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailVerifiedTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle, LoginAccountRateThrottle]
    throttle_scope = "login"


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def perform_create(self, serializer):
        user = serializer.save()
        services.send_verification_email(user, self.request)
        return user


class VerifyEmailView(APIView):
    """
    GET /api/v1/auth/verify-email/?uid=<uidb64>&token=<token>
    Validates the token and marks the email as verified.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        uidb64 = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uidb64 or not token:
            return Response(
                {"detail": "Missing verification parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success, message = services.verify_email_token(uidb64, token)
        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({"detail": message}, status=status_code)


class ConfirmEmailChangeView(APIView):
    """
    GET /api/v1/auth/confirm-email-change/?uid=<uidb64>&token=<token>
    Validates the token and applies a pending email change requested via
    MeView (see services.request_email_change).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        uidb64 = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uidb64 or not token:
            return Response(
                {"detail": "Missing confirmation parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success, message = services.confirm_email_change(uidb64, token)
        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({"detail": message}, status=status_code)


class ResendVerificationView(APIView):
    """
    POST /api/v1/auth/resend-verification/
    Body: {"email": "user@example.com"}
    Resends the verification email. Always returns 200 to prevent email enumeration.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_action"

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if email:
            try:
                user = User.objects.get(email=email)
                from allauth.account.models import EmailAddress
                if not EmailAddress.objects.filter(user=user, verified=True).exists():
                    services.send_verification_email(user, request)
            except User.DoesNotExist:
                pass  # Silently ignore to prevent email enumeration
        return Response(
            {"detail": "If an account exists with this email, a verification link has been sent."},
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        # Not a real delete — see services.delete_account for why.
        services.delete_account(instance)

    def perform_update(self, serializer):
        # Email routes through request_email_change instead of being
        # applied directly — see that function's docstring. Wrapped in one
        # transaction so a failure there (e.g. address already taken)
        # doesn't leave other fields (name, phone) silently saved anyway.
        new_email = serializer.validated_data.pop("email", None)
        with transaction.atomic():
            user = serializer.save()
            if new_email:
                services.request_email_change(user, new_email, self.request)


class AddressView(generics.RetrieveUpdateAPIView):
    """
    My Profile -> account settings: pickup address. get_or_create so a
    fresh user hitting GET doesn't 404 before ever setting one.
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return services.get_or_create_address(self.request.user)


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return services.get_or_create_notification_prefs(self.request.user)


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password-reset/
    Body: {"email": "user@example.com"}
    Always returns 200 to prevent email enumeration.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_action"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        user = User.objects.filter(email__iexact=email).first()
        if user and user.has_usable_password():
            services.send_password_reset_email(user, request)

        return Response(
            {"detail": "If an account exists with this email, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password-reset/confirm/
    Body: {"uid": "...", "token": "...", "new_password": "...", "new_password_confirm": "..."}
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_action"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        success, message = services.reset_password_with_token(
            serializer.validated_data["uid"],
            serializer.validated_data["token"],
            serializer.validated_data["new_password"],
        )
        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({"detail": message}, status=status_code)


class ChangePasswordView(APIView):
    """Checks old_password server-side, which makes this a password-
    guessing oracle for anyone holding a stolen access token — the same
    "login" scope login itself uses (ScopedRateThrottle keys authenticated
    requests by user id, not IP, so this isn't affected by IP-spoofing
    tricks either way)."""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.change_password(request.user, serializer.validated_data["new_password"])
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class FirebaseSocialLoginView(APIView):
    """
    POST {"id_token": "...", "display_name": "..."} (Firebase ID token from
    Google or Apple sign-in, obtained client-side via the Firebase SDK) ->
    returns the same JWT pair shape as the regular login endpoint.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        decoded_token, error = services.verify_firebase_token(request.data.get("id_token", ""))
        if error:
            return Response({"detail": error}, status=status.HTTP_401_UNAUTHORIZED)

        user = services.get_or_create_user_from_firebase(
            decoded_token, request.data.get("display_name", "")
        )
        # RefreshToken.for_user issues a token unconditionally — unlike the
        # password-login path, it doesn't go through authenticate(), which
        # is what actually enforces is_active there. Check it explicitly so
        # a banned account can't get in through social login instead.
        if not user.is_active:
            return Response(
                {"detail": "This account is not active."}, status=status.HTTP_401_UNAUTHORIZED
            )
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})
