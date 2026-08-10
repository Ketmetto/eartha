from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    VerifyEmailView,
    ConfirmEmailChangeView,
    ResendVerificationView,
    MeView,
    AddressView,
    NotificationPreferenceView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    FirebaseSocialLoginView,
    EmailVerifiedTokenObtainPairView,
)
from .admin_views import UserAdminListView, UserBanView, UserUnbanView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", EmailVerifiedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("confirm-email-change/", ConfirmEmailChangeView.as_view(), name="confirm-email-change"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("me/", MeView.as_view(), name="me"),
    path("me/address/", AddressView.as_view(), name="me-address"),
    path("me/notifications/", NotificationPreferenceView.as_view(), name="me-notifications"),
    path("me/change-password/", ChangePasswordView.as_view(), name="me-change-password"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("social/firebase/", FirebaseSocialLoginView.as_view(), name="firebase-login"),
    path("admin/users/", UserAdminListView.as_view(), name="admin-users"),
    path("admin/users/<int:pk>/ban/", UserBanView.as_view(), name="admin-users-ban"),
    path("admin/users/<int:pk>/unban/", UserUnbanView.as_view(), name="admin-users-unban"),
]
