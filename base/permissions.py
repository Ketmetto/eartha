from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Restricted-access admin dashboard routes."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsOwner(BasePermission):
    """Object-level check: request.user must own the object."""

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "user_id", None) == request.user.id
