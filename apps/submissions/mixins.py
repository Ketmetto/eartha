from rest_framework.response import Response
from apps.points.services import get_awarded_totals


class AwardedTotalsListMixin:
    """Batches ItemSerializer.get_awarded_points into one query for the
    whole list being serialized, instead of one per item — see that
    method and apps.points.services.get_awarded_totals."""

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        target = page if page is not None else queryset

        context = self.get_serializer_context()
        context["awarded_totals"] = get_awarded_totals(target)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, context=context)
        return Response(serializer.data)
