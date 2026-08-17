from rest_framework import generics, permissions
from rest_framework.throttling import ScopedRateThrottle
from .models import ImpactStat
from .serializers import ContactMessageSerializer, ImpactStatSerializer
from .services import notify_admin_of_contact_message


class ContactMessageCreateView(generics.CreateAPIView):
    """Public — no auth required. Every submission fires a real email to
    the admin (see notify_admin_of_contact_message), so this needs a
    tighter cap than the generic anon default — see the "contact" scope's
    comment in DEFAULT_THROTTLE_RATES."""
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    def perform_create(self, serializer):
        message = serializer.save()
        notify_admin_of_contact_message(message)


class ImpactStatsView(generics.RetrieveAPIView):
    """Public — powers the About page impact numbers."""
    serializer_class = ImpactStatSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        # Singleton row, admin-edited — self-heals on a fresh DB (no
        # fixture/seed run yet) instead of returning None, which the
        # serializer would otherwise silently turn into null fields.
        return ImpactStat.objects.first() or ImpactStat.objects.create()
