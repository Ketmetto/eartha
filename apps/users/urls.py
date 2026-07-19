from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView,
    VerifyEmailView,
    ResendVerificationView,
    MeView,
    AddressView,
    NotificationPreferenceView,
    ChangePasswordView,
    GoogleLoginView,
    AppleLoginView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("me/", MeView.as_view(), name="me"),
    path("me/address/", AddressView.as_view(), name="me-address"),
    path("me/notifications/", NotificationPreferenceView.as_view(), name="me-notifications"),
    path("me/change-password/", ChangePasswordView.as_view(), name="me-change-password"),
    path("social/google/", GoogleLoginView.as_view(), name="google-login"),
    path("social/apple/", AppleLoginView.as_view(), name="apple-login"),
]
