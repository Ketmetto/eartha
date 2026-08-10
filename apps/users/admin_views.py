from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from base.pagination import StandardResultsPagination
from base.permissions import IsAdmin
from .models import User
from .serializers import UserAdminSerializer, BanUserSerializer
from . import services


class UserStatsListMixin:
    """Batches UserAdminSerializer's counts into one set of queries for
    the whole page being serialized, instead of one per user — same idea
    as apps.submissions.mixins.AwardedTotalsListMixin."""

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        target = page if page is not None else queryset

        context = self.get_serializer_context()
        context["user_stats"] = services.get_user_stats(target)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, context=context)
        return Response(serializer.data)


class UserAdminListView(UserStatsListMixin, generics.ListAPIView):
    """Admin: the Users page — every account, most recent signup first.
    ?search= matches email or name (case-insensitive, partial)."""
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        queryset = User.objects.all().order_by("-date_joined")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
            )
        return queryset


class UserBanView(APIView):
    """Admin: ban a user (blocks login, keeps everything else — see
    services.ban_user). POST {"reason": "..."}"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)
        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot ban your own account."}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = BanUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.ban_user(user, reason=serializer.validated_data["reason"])
        return Response(UserAdminSerializer(user).data, status=status.HTTP_200_OK)


class UserUnbanView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)
        services.unban_user(user)
        return Response(UserAdminSerializer(user).data, status=status.HTTP_200_OK)
