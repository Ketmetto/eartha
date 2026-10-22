from django.urls import path
from django.views.generic import RedirectView
from .views import (
    IndexView,
    AboutView,
    BenefitsView,
    ContactView,
    WishlistRequestView,
    ShopView,
    ShopManageView,
    DashboardView,
    LoginView,
    ProfileView,
    QueueView,
    UsersView,
    ContentView,
    TermsView,
    UploadView,
    VerifyEmailPageView,
    NewsletterConfirmPageView,
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
    path("shop/", ShopView.as_view(), name="shop"),
    path("shop/manage/", ShopManageView.as_view(), name="shop-manage"),
    path("wishlist/request/", WishlistRequestView.as_view(), name="wishlist-request"),
    path("verify-email/", VerifyEmailPageView.as_view(), name="verify-email"),
    path("newsletter/confirm/", NewsletterConfirmPageView.as_view(), name="newsletter-confirm"),
    path("confirm-email-change/", ConfirmEmailChangePageView.as_view(), name="confirm-email-change"),
    path("reset-password/", ResetPasswordPageView.as_view(), name="reset-password"),
    path("verify/<str:code>/", VoucherVerifyView.as_view(), name="verify"),

    # Redirects for the site's original static-prototype filenames — old
    # bookmarks/home-screen icons saved before the domain pointed here
    # still request these exact paths (see the 404s from a client's iPhone
    # for /contact.html and /index.html, confirmed via nginx access logs).
    path("index.html", RedirectView.as_view(pattern_name="web:index", permanent=True)),
    path("about.html", RedirectView.as_view(pattern_name="web:about", permanent=True)),
    path("benefits.html", RedirectView.as_view(pattern_name="web:benefits", permanent=True)),
    path("contact.html", RedirectView.as_view(pattern_name="web:contact", permanent=True)),
    path("dashboard.html", RedirectView.as_view(pattern_name="web:dashboard", permanent=True)),
    path("login.html", RedirectView.as_view(pattern_name="web:login", permanent=True)),
    path("profile.html", RedirectView.as_view(pattern_name="web:profile", permanent=True)),
    path("queue.html", RedirectView.as_view(pattern_name="web:queue", permanent=True)),
    path("upload.html", RedirectView.as_view(pattern_name="web:upload", permanent=True)),
]
