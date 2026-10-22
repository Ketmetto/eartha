"""Staff-only API behind the /shop/manage/ page — the admin-friendly
alternative to the Django admin for running the shop day to day."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from base.permissions import IsAdmin
from base.validators import validate_image_content_type, validate_image_size

from .models import Order, Product
from .serializers import OrderAdminSerializer, OrderStatusSerializer, ProductAdminSerializer
from .services import replace_product_photos, set_order_status

MAX_PRODUCT_PHOTOS = 8


def _validated_photos(request, required):
    photos = request.FILES.getlist("photos")
    if required and not photos:
        raise ValidationError({"photos": ["Add at least one photo."]})
    if len(photos) > MAX_PRODUCT_PHOTOS:
        raise ValidationError({"photos": [f"Up to {MAX_PRODUCT_PHOTOS} photos per product."]})
    for photo in photos:
        try:
            validate_image_size(photo)
            validate_image_content_type(photo)
        except DjangoValidationError as exc:
            raise ValidationError({"photos": exc.messages})
    return photos


class ProductAdminListCreateView(generics.ListCreateAPIView):
    """Every product, published or not, newest first. POST is multipart:
    product fields plus one or more `photos`."""
    serializer_class = ProductAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        return Product.objects.prefetch_related("extra_images").order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photos = _validated_photos(request, required=True)
        with transaction.atomic():
            product = Product(**serializer.validated_data)
            replace_product_photos(product, photos)
        return Response(self.get_serializer(product).data, status=status.HTTP_201_CREATED)


class ProductAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH is multipart; any `photos` sent replace all existing ones."""
    serializer_class = ProductAdminSerializer
    permission_classes = [IsAdmin]
    queryset = Product.objects.prefetch_related("extra_images")

    def update(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        photos = _validated_photos(request, required=False)
        with transaction.atomic():
            product = serializer.save()
            if photos:
                replace_product_photos(product, photos)
        product = self.get_queryset().get(pk=product.pk)
        return Response(self.get_serializer(product).data)


class OrderAdminListView(generics.ListAPIView):
    """?view=open (new + confirmed, oldest first — work through them in
    order) or ?view=done (delivered + cancelled, newest first, last 200)."""
    serializer_class = OrderAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        qs = Order.objects.prefetch_related("items")
        if self.request.query_params.get("view") == "done":
            return qs.filter(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).order_by("-created_at")[:200]
        return qs.filter(status__in=[Order.Status.NEW, Order.Status.CONFIRMED]).order_by("created_at")


class OrderStatusView(APIView):
    """POST {"status": "confirmed" | "delivered" | "cancelled"}."""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        order = generics.get_object_or_404(Order, pk=pk)
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = set_order_status(order, serializer.validated_data["status"])
        order = Order.objects.prefetch_related("items").get(pk=order.pk)
        return Response(OrderAdminSerializer(order).data)


class NewOrderCountView(APIView):
    """Badge count for the admin nav / SHOP tab."""
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"new": Order.objects.filter(status=Order.Status.NEW).count()})
