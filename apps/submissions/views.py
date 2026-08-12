from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .mixins import AwardedTotalsListMixin
from .models import Item
from .serializers import ItemSerializer, ItemCreateWithPhotosSerializer
from .services import create_item_with_photos


class ItemUploadView(AwardedTotalsListMixin, generics.ListCreateAPIView):
    """User-facing: submit a new item, list own submissions. The list side
    uses the default pagination (base.pagination.StandardResultsPagination)
    — a long-time user's submission history can grow past what's
    comfortable to ship in one response."""
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Item.objects.filter(user=self.request.user)

    # Only POST gets the tighter cap — up to 10 photos per submission
    # means the generic default alone would allow 10,000 photos/hour from
    # one account. Browsing your own history isn't a spam vector.
    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "item_upload"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def create(self, request, *args, **kwargs):
        """Accepts multipart/form-data with item fields + photos."""
        input_serializer = ItemCreateWithPhotosSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        validated = input_serializer.validated_data

        photos = request.FILES.getlist("photos")
        if not photos:
            return Response(
                {"photos": ["At least one photo is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        item = create_item_with_photos(
            user=request.user,
            category=validated["category"],
            condition=validated["condition"],
            description=validated.get("description", ""),
            photos=photos,
        )

        output_serializer = self.get_serializer(item)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
