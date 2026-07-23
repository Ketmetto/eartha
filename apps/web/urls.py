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
    UploadView,
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
    path("upload/", UploadView.as_view(), name="upload"),
]
