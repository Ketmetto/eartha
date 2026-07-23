from rest_framework import generics, status
from rest_framework.response import Response
from base.permissions import IsAdmin
from .models import Item
from .serializers import (
    ItemAdminSerializer,
    SubmissionDecisionSerializer,
    DriverDispatchSerializer,
)
from .services import transition_item_status, assign_driver


class SubmissionReviewQueueView(generics.ListAPIView):
    """Admin: pending submissions queue."""
    serializer_class = ItemAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    queryset = Item.objects.filter(status=Item.Status.PENDING)


class SubmissionDecisionView(generics.GenericAPIView):
    """
    Admin: accept or reject an item.

    Drives the state machine — admins cannot set status to arbitrary values.
    POST /admin/<uuid:pk>/decision/
      {"action": "accept"}
      or
      {"action": "reject", "rejection_reason": "..."}
    """
    serializer_class = SubmissionDecisionSerializer
    permission_classes = [IsAdmin]
    queryset = Item.objects.all()

    def post(self, request, *args, **kwargs):
        item = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        rejection_reason = serializer.validated_data.get("rejection_reason", "")

        if action == "accept":
            item = transition_item_status(item, Item.Status.ACCEPTED)
        elif action == "reject":
            item = transition_item_status(
                item, Item.Status.REJECTED, reason=rejection_reason
            )

        return Response(
            ItemAdminSerializer(item).data,
            status=status.HTTP_200_OK
        )


class DriverDispatchView(generics.GenericAPIView):
    """
    Admin: assign a driver to an accepted item.

    POST /admin/<uuid:pk>/dispatch/
      {"driver_name": "...", "pickup_address_snapshot": "..."}
    Creates a DriverAssignment and transitions the item to DISPATCHED.
    """
    serializer_class = DriverDispatchSerializer
    permission_classes = [IsAdmin]
    queryset = Item.objects.all()

    def post(self, request, *args, **kwargs):
        item = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment = assign_driver(
            item=item,
            driver_name=serializer.validated_data["driver_name"],
            pickup_address_snapshot=serializer.validated_data["pickup_address_snapshot"],
        )

        return Response(
            {"detail": "Driver assigned and item dispatched.", "assignment_id": str(assignment.id)},
            status=status.HTTP_201_CREATED
        )
