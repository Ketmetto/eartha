from django.urls import path
from .views import ContactMessageCreateView, ImpactStatsView

urlpatterns = [
    path("contact/", ContactMessageCreateView.as_view(), name="contact-create"),
    path("impact-stats/", ImpactStatsView.as_view(), name="impact-stats"),
]
