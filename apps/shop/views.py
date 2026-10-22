from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from base.form_guard import FormTokenExpired

from .serializers import OrderCreateSerializer
from .services import check_order_form_token, place_order


class OrderCreateView(APIView):
    """
    POST /api/v1/shop/orders/
    Public — cash-on-delivery checkout, no account needed. Same spam
    defenses as WishlistRequestCreateView: the "shop_order" throttle, a
    `website` honeypot and a signed page-load token. A bot-flagged order
    gets a plausible success response but is never placed, so it can't
    reserve real stock.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "shop_order"

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = data.pop("items")
        honeypot = data.pop("website", "")
        token = data.pop("form_token")

        try:
            human_paced = check_order_form_token(token)
        except FormTokenExpired:
            return Response(
                {"detail": "This page has expired. Refresh it and try again — your basket is saved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if honeypot or not human_paced:
            return Response({"order": "RECEIVED"}, status=status.HTTP_201_CREATED)

        order = place_order(lines=lines, **data)
        return Response(
            {"order": order.number, "total_usd": f"{order.total_usd:.2f}"},
            status=status.HTTP_201_CREATED,
        )
