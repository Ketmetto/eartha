from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from .models import User, Address, NotificationPreference


class UserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "verified")
    list_editable = ("verified",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Test access", {"fields": ("verified",)}),
    )


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
