from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .models import ImpactStat
from .serializers import ContactMessageSerializer, ImpactStatSerializer, NewsletterSubscribeSerializer
from .services import confirm_newsletter_subscription, notify_admin_of_contact_message, subscribe_to_newsletter


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


class NewsletterSubscribeView(APIView):
    """
    POST /api/v1/engagement/newsletter/
    Public. Emails a confirmation link (double opt-in). Always returns the
    same 200 whether the address is new, pending, or already confirmed, so
    the form can't be used to probe the list.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "newsletter"

    def post(self, request):
        serializer = NewsletterSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscribe_to_newsletter(serializer.validated_data["email"], request)
        return Response({"detail": "Check your inbox to confirm your subscription."})


class NewsletterConfirmView(APIView):
    """
    GET /api/v1/engagement/newsletter/confirm/?token=<token>
    Called by the /newsletter/confirm/ page the emailed link opens.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"detail": "Missing confirmation parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success, message = confirm_newsletter_subscription(token)
        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({"detail": message}, status=status_code)
