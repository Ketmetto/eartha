from django.db.models import Sum
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .models import PointsLedgerEntry, Benefit, Redemption
from .serializers import PointsLedgerEntrySerializer, BenefitSerializer, RedemptionSerializer
from .services import redeem_benefit


class BalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total = PointsLedgerEntry.objects.filter(user=request.user).aggregate(total=Sum("points"))["total"] or 0
        return Response({"balance": total})


class LedgerHistoryView(generics.ListAPIView):
    serializer_class = PointsLedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PointsLedgerEntry.objects.filter(user=self.request.user)


class BenefitListView(generics.ListAPIView):
    serializer_class = BenefitSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = Benefit.objects.filter(is_active=True).order_by("display_priority")
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class RedeemBenefitView(generics.CreateAPIView):
    serializer_class = RedemptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "redeem"

    def perform_create(self, serializer):
        benefit = serializer.validated_data["benefit"]
        serializer.instance = redeem_benefit(user=self.request.user, benefit=benefit)


class MyRedemptionsView(generics.ListAPIView):
    """The authenticated user's own redemption history. Default pagination
    (base.pagination.StandardResultsPagination) — bounded by individual
    usage, but a long-time user could still build up enough of these to be
    worth loading a page at a time."""
    serializer_class = RedemptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Redemption.objects.filter(user=self.request.user).select_related("benefit")
