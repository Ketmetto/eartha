from rest_framework import generics, permissions
from .models import ContactMessage, ImpactStat
from .serializers import ContactMessageSerializer, ImpactStatSerializer


class ContactMessageCreateView(generics.CreateAPIView):
    """Public — no auth required."""
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]


class ImpactStatsView(generics.RetrieveAPIView):
    """Public — powers the About page impact numbers."""
    serializer_class = ImpactStatSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return ImpactStat.objects.first()
