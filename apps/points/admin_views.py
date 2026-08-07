from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from base.permissions import IsAdmin
from apps.submissions.models import Item
from .models import Benefit
from .serializers import BenefitAdminSerializer, BenefitReorderSerializer, ItemAwardSerializer
from .services import set_item_award, get_awarded_total


class BenefitAdminListCreateView(generics.ListCreateAPIView):
    """Admin: full benefit catalog (including inactive) + create new benefits."""
    serializer_class = BenefitAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = Benefit.objects.all().order_by("display_priority")
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class BenefitAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: edit, activate/deactivate, or remove a benefit."""
    serializer_class = BenefitAdminSerializer
    permission_classes = [IsAdmin]
    queryset = Benefit.objects.all()


class BenefitReorderView(APIView):
    """
    Admin: set display order in one shot.
    POST {"ids": [uuid, uuid, ...]} — front-to-back order for the benefits page.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BenefitReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        benefits = {b.id: b for b in Benefit.objects.filter(id__in=ids)}
        for priority, benefit_id in enumerate(ids):
            benefit = benefits.get(benefit_id)
            if benefit:
                benefit.display_priority = priority
        Benefit.objects.bulk_update(
            [b for b in benefits.values()], ["display_priority"]
        )
        return Response({"detail": "Display order updated."}, status=status.HTTP_200_OK)


class ItemAwardView(generics.GenericAPIView):
    """
    Admin: award or correct the points for a submission, at discretion,
    any time from COLLECTED status onward — never automatic on accept or
    dispatch, since neither confirms the item is actually in hand yet.
    POST /admin/items/<uuid:pk>/award/  {"points": 70}
    """
    serializer_class = ItemAwardSerializer
    permission_classes = [IsAdmin]
    queryset = Item.objects.all()

    def post(self, request, *args, **kwargs):
        item = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        set_item_award(item, serializer.validated_data["points"], request.user)

        return Response({"awarded_points": get_awarded_total(item)}, status=status.HTTP_200_OK)
