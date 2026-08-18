from io import BytesIO

import qrcode
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .models import PointsLedgerEntry, Benefit, Redemption
from .serializers import PointsLedgerEntrySerializer, BenefitSerializer, RedemptionSerializer, RedemptionVerifySerializer
from .services import redeem_benefit, mark_redemption_used


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


class RedemptionQRCodeView(APIView):
    """Serves the customer's own voucher as a QR-code PNG, encoding the
    public verify URL. Owner-scoped + authenticated — this endpoint isn't
    itself the public "is this code real?" check (RedemptionVerifyView is),
    it just hands the owning customer an image of a link that IS public."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        redemption = get_object_or_404(Redemption, pk=pk, user=request.user)
        url = f"{settings.SITE_URL}/verify/{redemption.code}/"
        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return HttpResponse(buf.getvalue(), content_type="image/png")


class RedemptionVerifyView(generics.RetrieveAPIView):
    """Public — the merchant-facing "is this code real?" check, looked up
    by code (the only thing on the QR/screen), not pk. No PII in the
    response — see RedemptionVerifySerializer."""
    serializer_class = RedemptionVerifySerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify"
    lookup_field = "code"
    queryset = Redemption.objects.select_related("benefit")


class RedemptionRedeemView(APIView):
    """Public — the merchant confirms redemption. mark_redemption_used is
    race-safe (select_for_update), so two near-simultaneous confirms on the
    same code can't both succeed."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "verify"

    def post(self, request, code):
        redemption = mark_redemption_used(code)
        return Response(RedemptionVerifySerializer(redemption).data)
