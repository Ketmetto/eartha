from django.urls import path
from .views import (
    IndexView,
    AboutView,
    BenefitsView,
    ContactView,
    DashboardView,
    LoginView,
    ProfileView,
    QueueView,
    UsersView,
    ContentView,
    TermsView,
    UploadView,
    VerifyEmailPageView,
    ConfirmEmailChangePageView,
    ResetPasswordPageView,
    VoucherVerifyView,
)

app_name = "web"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("about/", AboutView.as_view(), name="about"),
    path("benefits/", BenefitsView.as_view(), name="benefits"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("queue/", QueueView.as_view(), name="queue"),
    path("users/", UsersView.as_view(), name="users"),
    path("content/", ContentView.as_view(), name="content"),
    path("terms/", TermsView.as_view(), name="terms"),
    path("upload/", UploadView.as_view(), name="upload"),
    path("verify-email/", VerifyEmailPageView.as_view(), name="verify-email"),
    path("confirm-email-change/", ConfirmEmailChangePageView.as_view(), name="confirm-email-change"),
    path("reset-password/", ResetPasswordPageView.as_view(), name="reset-password"),
    path("verify/<str:code>/", VoucherVerifyView.as_view(), name="verify"),
]
