from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address, NotificationPreference


class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "verified")
    list_editable = ("verified",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Test access", {"fields": ("verified",)}),
    )


admin.site.register(User, UserAdmin)
admin.site.register(Address)
admin.site.register(NotificationPreference)
