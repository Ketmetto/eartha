from rest_framework import generics, permissions
from .models import ImpactStat
from .serializers import ContactMessageSerializer, ImpactStatSerializer
from .services import notify_admin_of_contact_message


class ContactMessageCreateView(generics.CreateAPIView):
    """Public — no auth required."""
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        message = serializer.save()
        notify_admin_of_contact_message(message)


class ImpactStatsView(generics.RetrieveAPIView):
    """Public — powers the About page impact numbers."""
    serializer_class = ImpactStatSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return ImpactStat.objects.first()
