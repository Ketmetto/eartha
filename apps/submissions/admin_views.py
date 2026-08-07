from rest_framework import generics, status
from rest_framework.response import Response
from base.pagination import StandardResultsPagination
from base.permissions import IsAdmin
from .models import Item, Driver
from .serializers import (
    ItemAdminSerializer,
    SubmissionDecisionSerializer,
    DriverDispatchSerializer,
    DriverReassignSerializer,
    DriverSerializer,
)
from .services import transition_item_status, assign_driver, reassign_driver

ACTION_STATUSES = [Item.Status.PENDING, Item.Status.ACCEPTED, Item.Status.DISPATCHED, Item.Status.COLLECTED]
DONE_STATUSES = [Item.Status.COMPLETED, Item.Status.REJECTED]


class SubmissionReviewQueueView(generics.ListAPIView):
    """Admin: pending submissions queue."""
    serializer_class = ItemAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    queryset = Item.objects.filter(status=Item.Status.PENDING)


class SubmissionAdminListView(generics.ListAPIView):
    """Admin: the working backlog — everything from pending through collected,
    i.e. still needs an admin to do something with it. Unpaginated on purpose:
    unlike the completed/rejected history below, this stays naturally bounded
    by how fast the queue gets worked, so there's no unbounded-growth risk."""
    serializer_class = ItemAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    queryset = Item.objects.filter(
        status__in=ACTION_STATUSES
    ).select_related("user", "user__address").order_by("-updated_at")


class SubmissionAdminDoneListView(generics.ListAPIView):
    """Admin: completed/rejected submission history. Paginated — unlike the
    action queue above, this list only ever grows, so returning it in full
    (previously done via SubmissionAdminListView before it was split) would
    eventually mean shipping the entire submission history to the browser
    on every queue page load."""
    serializer_class = ItemAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsPagination
    queryset = Item.objects.filter(
        status__in=DONE_STATUSES
    ).select_related("user", "user__address").order_by("-updated_at")


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


class DriverAdminListCreateView(generics.ListCreateAPIView):
    """Admin: the driver roster the dispatch dropdown is populated from."""
    serializer_class = DriverSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    queryset = Driver.objects.all()


class DriverAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: edit or remove a driver from the roster."""
    serializer_class = DriverSerializer
    permission_classes = [IsAdmin]
    queryset = Driver.objects.all()


class DriverDispatchView(generics.GenericAPIView):
    """
    Admin: assign a driver to an accepted item.

    POST /admin/<uuid:pk>/dispatch/
      {"driver_name": "...", "pickup_address_snapshot": "..."}
    pickup_address_snapshot is optional — falls back to the user's saved
    address (see services.assign_driver) if omitted.
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
            pickup_address_snapshot=serializer.validated_data.get("pickup_address_snapshot", ""),
        )

        return Response(
            {"detail": "Driver assigned and item dispatched.", "assignment_id": str(assignment.id)},
            status=status.HTTP_201_CREATED
        )


class DriverReassignView(generics.GenericAPIView):
    """
    Admin: correct the driver on an already-dispatched item, from the
    website — previously the only way to fix a wrong assignment was
    editing DriverAssignment directly in Django admin.

    POST /admin/<uuid:pk>/reassign-driver/  {"driver_name": "..."}
    Only legal while the item is still DISPATCHED.
    """
    serializer_class = DriverReassignSerializer
    permission_classes = [IsAdmin]
    queryset = Item.objects.all()

    def post(self, request, *args, **kwargs):
        item = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reassign_driver(item=item, driver_name=serializer.validated_data["driver_name"])

        return Response(ItemAdminSerializer(item).data, status=status.HTTP_200_OK)


class SubmissionMarkCollectedView(generics.GenericAPIView):
    """Admin: mark a dispatched item as collected. POST /admin/<uuid:pk>/collect/"""
    permission_classes = [IsAdmin]
    queryset = Item.objects.all()

    def post(self, request, *args, **kwargs):
        item = transition_item_status(self.get_object(), Item.Status.COLLECTED)
        return Response(ItemAdminSerializer(item).data, status=status.HTTP_200_OK)


class SubmissionMarkCompletedView(generics.GenericAPIView):
    """
    Admin: mark a collected item as completed, closing out the pipeline.
    POST /admin/<uuid:pk>/complete/
    This transition itself has no points effect — points can be awarded or
    corrected any time from DISPATCHED status onward (including on a
    COMPLETED item) via apps.points.admin_views.ItemAwardView, independent
    of this status change.
    """
    permission_classes = [IsAdmin]
    queryset = Item.objects.all()

    def post(self, request, *args, **kwargs):
        item = transition_item_status(self.get_object(), Item.Status.COMPLETED)
        return Response(ItemAdminSerializer(item).data, status=status.HTTP_200_OK)
