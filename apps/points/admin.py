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
    # search_fields is what makes this actually useful for the "is this
    # code real?" phone call from a partner store — list_display alongside
    # it since Redemption has no __str__, so the list would otherwise just
    # show unhelpful "Redemption object (<uuid>)" rows.
    search_fields = ("code",)
    list_display = ("code", "user", "benefit", "points_spent", "created_at")
