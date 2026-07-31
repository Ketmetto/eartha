from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ContactMessage, ImpactStat


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    pass


@admin.register(ImpactStat)
class ImpactStatAdmin(ModelAdmin):
    pass
