from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SiteText, SiteImage


@admin.register(SiteText)
class SiteTextAdmin(ModelAdmin):
    list_display = ("key", "value")


@admin.register(SiteImage)
class SiteImageAdmin(ModelAdmin):
    list_display = ("key", "image")
