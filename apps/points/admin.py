from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import PointsLedgerEntry, Benefit, Redemption


@admin.register(PointsLedgerEntry)
class PointsLedgerEntryAdmin(ModelAdmin):
    pass


@admin.register(Benefit)
class BenefitAdmin(ModelAdmin):
    pass


@admin.register(Redemption)
class RedemptionAdmin(ModelAdmin):
    pass
