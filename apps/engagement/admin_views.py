from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from base.pagination import StandardResultsPagination
from base.permissions import IsAdmin
from .models import ContactMessage
from .serializers import ContactMessageAdminSerializer


class ContactMessageAdminListView(generics.ListAPIView):
    """Admin inbox: every contact-form message, newest first. Paginated —
    the public contact form is unauthenticated and open to anyone, so
    unlike most admin lists this one has no natural bound on how large it
    can grow.

    ?resolved=true/false filters by read state — used on its own with
    page_size=1 (see StandardResultsPagination) purely to read the
    paginated envelope's `count`, i.e. a cheap accurate unread badge that
    doesn't depend on how many pages of the inbox have actually been
    loaded client-side."""
    serializer_class = ContactMessageAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        queryset = ContactMessage.objects.all()
        resolved = self.request.query_params.get("resolved")
        if resolved is not None:
            queryset = queryset.filter(resolved=resolved.lower() == "true")
        return queryset


class ContactMessageResolveView(APIView):
    """Admin: mark a message resolved (used as the 'read' flag by the inbox UI)."""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        message = generics.get_object_or_404(ContactMessage, pk=pk)
        message.resolved = True
        message.save(update_fields=["resolved", "updated_at"])
        return Response(ContactMessageAdminSerializer(message).data, status=status.HTTP_200_OK)


class AdminDashboardStatsView(APIView):
    """
    Admin dashboard homepage: aggregate counts across submissions, points,
    users and messages, plus a short recent-activity feed. One call powers
    the whole /dashboard/ page instead of the frontend stitching together
    several list endpoints and computing totals client-side.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.submissions.models import Item
        from apps.submissions.serializers import ItemAdminSerializer
        from apps.points.models import PointsLedgerEntry, Benefit
        from apps.users.models import User

        pending_count = Item.objects.filter(status=Item.Status.PENDING).count()
        in_progress_count = Item.objects.filter(
            status__in=[Item.Status.ACCEPTED, Item.Status.DISPATCHED, Item.Status.COLLECTED]
        ).count()
        completed_count = Item.objects.filter(status=Item.Status.COMPLETED).count()
        unread_messages_count = ContactMessage.objects.filter(resolved=False).count()
        total_points_awarded = PointsLedgerEntry.objects.filter(
            entry_type=PointsLedgerEntry.EntryType.AWARD
        ).aggregate(total=Sum("points"))["total"] or 0
        donor_count = User.objects.filter(is_staff=False).count()
        live_benefits_count = Benefit.objects.filter(is_active=True).count()

        recent_items = Item.objects.all().select_related(
            "user", "user__address"
        ).order_by("-updated_at")[:6]

        return Response({
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
            "completed_count": completed_count,
            "unread_messages_count": unread_messages_count,
            "total_points_awarded": total_points_awarded,
            "donor_count": donor_count,
            "live_benefits_count": live_benefits_count,
            "recent_items": ItemAdminSerializer(recent_items, many=True).data,
        })
