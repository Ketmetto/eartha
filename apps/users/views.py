from decouple import config
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from .models import User
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    AddressSerializer,
    NotificationPreferenceSerializer,
    ChangePasswordSerializer,
)
from . import services


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Send verification email after registration
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


class ResendVerificationView(APIView):
    """
    POST /api/v1/auth/resend-verification/
    Body: {"email": "user@example.com"}
    Resends the verification email. Always returns 200 to prevent email enumeration.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if email:
            try:
                user = User.objects.get(email=email)
                # Only resend if not already verified
                from allauth.account.models import EmailAddress
                if not EmailAddress.objects.filter(user=user, verified=True).exists():
                    services.send_verification_email(user, request)
            except User.DoesNotExist:
                pass  # Silently ignore to prevent email enumeration
        return Response(
            {"detail": "If an account exists with this email, a verification link has been sent."},
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


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


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.change_password(request.user, serializer.validated_data["new_password"])
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class GoogleLoginView(SocialLoginView):
    """
    POST {"access_token": "..."} (token obtained client-side via Google's
    SDK) -> returns the same JWT pair shape as the regular login endpoint.
    """
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = config("GOOGLE_CALLBACK_URL", default="")


class AppleLoginView(SocialLoginView):
    """POST {"access_token": "..."} (Apple identity token) -> JWT pair."""
    adapter_class = AppleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = config("APPLE_CALLBACK_URL", default="")
