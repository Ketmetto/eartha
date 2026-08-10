from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from base.permissions import IsAdmin
from .models import SiteText, SiteImage
from .serializers import SiteTextAdminSerializer, SiteImageAdminSerializer


class SiteTextAdminListView(generics.ListAPIView):
    """Admin: every editable text slot on the public marketing pages."""
    serializer_class = SiteTextAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    queryset = SiteText.objects.all().order_by("key")


class SiteTextAdminUpdateView(generics.RetrieveUpdateAPIView):
    """Admin: replace one text slot's value. No create/delete — the set of
    keys is fixed (see SiteText.Key), seeded by a migration."""
    serializer_class = SiteTextAdminSerializer
    permission_classes = [IsAdmin]
    queryset = SiteText.objects.all()
    lookup_field = "key"


class SiteImageAdminListView(generics.ListAPIView):
    """Admin: every editable image slot on the public marketing pages."""
    serializer_class = SiteImageAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    queryset = SiteImage.objects.all().order_by("key")


class SiteImageAdminUpdateView(generics.RetrieveUpdateAPIView):
    """Admin: replace one image slot. Same fixed-set convention as
    SiteTextAdminUpdateView."""
    serializer_class = SiteImageAdminSerializer
    permission_classes = [IsAdmin]
    queryset = SiteImage.objects.all()
    lookup_field = "key"


class SiteImageAdminClearView(APIView):
    """Admin: clear a slot's uploaded image, reverting the public page to
    its original built-in asset (see SiteImage.image's docstring)."""
    permission_classes = [IsAdmin]

    def post(self, request, key):
        image = generics.get_object_or_404(SiteImage, key=key)
        image.image.delete(save=False)
        image.image = None
        image.save(update_fields=["image"])
        return Response(SiteImageAdminSerializer(image).data)
