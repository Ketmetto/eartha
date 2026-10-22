import csv

from django.contrib import admin
from django.http import HttpResponse
from unfold.admin import ModelAdmin
from .models import ContactMessage, ImpactStat, NewsletterSubscriber


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    pass


@admin.register(ImpactStat)
class ImpactStatAdmin(ModelAdmin):
    pass


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ModelAdmin):
    list_display = ["email", "created_at", "confirmed_at"]
    list_filter = [("confirmed_at", admin.EmptyFieldListFilter)]
    search_fields = ["email"]
    actions = ["export_csv"]

    @admin.action(description="Export selected to CSV (confirmed only)")
    def export_csv(self, request, queryset):
        # Unconfirmed addresses are skipped — they never clicked the
        # double opt-in link, so they haven't actually agreed to receive
        # anything. Plain email + date columns — the shape Brevo's contact
        # import (and most other campaign tools) accepts as-is.
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="newsletter_subscribers.csv"'
        writer = csv.writer(response)
        writer.writerow(["email", "confirmed_at"])
        for sub in queryset.filter(confirmed_at__isnull=False).order_by("confirmed_at"):
            email = sub.email
            # A valid address can start with "=", "+", "-" or "@", which
            # Excel/Sheets would run as a formula — neutralize it.
            if email[0] in "=+-@":
                email = "'" + email
            writer.writerow([email, sub.confirmed_at.isoformat()])
        return response
