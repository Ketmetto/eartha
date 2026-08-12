from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import User, Address, NotificationPreference


class UserAdmin(BaseUserAdmin, ModelAdmin):
    # No custom bulk actions here — django-unfold's action dropdown is
    # Alpine.js-driven (x-model, not a native <select>), and ban/unban as
    # bulk actions weren't reliably submitting in testing. Individual
    # ban/unban already works both here (via the "Active" checkbox below)
    # and on the site's own /users/ admin page, which is the reliable path
    # for this.
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "verified", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Test access", {"fields": ("verified",)}),
        ("Ban", {"fields": ("ban_reason", "banned_at")}),
    )
    readonly_fields = BaseUserAdmin.readonly_fields + ("banned_at",)

    def save_model(self, request, obj, form, change):
        # Editing "Active" directly on the change form keeps banned_at/
        # ban_reason in sync too — set on `obj` here (not via
        # services.ban_user/unban_user's own partial save, which would
        # drop any other field edited in the same submit) so the single
        # super().save_model() call below persists everything together.
        if change and "is_active" in form.changed_data:
            if obj.is_active:
                obj.ban_reason = ""
                obj.banned_at = None
            else:
                obj.banned_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    pass


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    pass


admin.site.register(User, UserAdmin)

# Restyle the default auth Group admin to match — it's auto-registered by
# django.contrib.auth with a plain admin.ModelAdmin otherwise.
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    pass
