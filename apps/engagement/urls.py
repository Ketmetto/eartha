from django.urls import path
from .views import ContactMessageCreateView, ImpactStatsView, NewsletterConfirmView, NewsletterSubscribeView
from .admin_views import ContactMessageAdminListView, ContactMessageResolveView, AdminDashboardStatsView

urlpatterns = [
    path("contact/", ContactMessageCreateView.as_view(), name="contact-create"),
    path("newsletter/", NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
    path("newsletter/confirm/", NewsletterConfirmView.as_view(), name="newsletter-confirm"),
    path("impact-stats/", ImpactStatsView.as_view(), name="impact-stats"),
    path("admin/messages/", ContactMessageAdminListView.as_view(), name="messages-admin-list"),
    path("admin/messages/<uuid:pk>/resolve/", ContactMessageResolveView.as_view(), name="messages-admin-resolve"),
    path("admin/stats/", AdminDashboardStatsView.as_view(), name="admin-dashboard-stats"),
]
