from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import PointsLedgerEntry, Benefit, PointsRule, Redemption


@admin.register(PointsLedgerEntry)
class PointsLedgerEntryAdmin(ModelAdmin):
    pass


@admin.register(PointsRule)
class PointsRuleAdmin(ModelAdmin):
    # Primary edit surface is the queue page's AWARD RULES tab — this is
    # just a fallback/debug view, so no need for a fancier list display.
    list_display = ("category", "condition", "points")


@admin.register(Benefit)
class BenefitAdmin(ModelAdmin):
    pass


@admin.register(Redemption)
class RedemptionAdmin(ModelAdmin):
    pass
