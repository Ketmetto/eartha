from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import Item, ItemPhoto, DriverAssignment
from .services import transition_item_status
from .state_machine import can_transition


class ItemAdminForm(forms.ModelForm):
    """Validates a status change against the state machine + points-reversal
    feasibility at form-clean time, so an illegal edit re-renders the change
    form with a clear error instead of silently corrupting data (which is
    what a plain field save would otherwise do — see ItemAdmin.save_model)."""
    class Meta:
        model = Item
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        new_status = cleaned.get("status")
        if self.instance.pk and new_status:
            old_status = Item.objects.get(pk=self.instance.pk).status
            if new_status != old_status:
                if not can_transition(old_status, new_status):
                    self.add_error("status", f"Cannot move item from {old_status} to {new_status}.")
                elif old_status == Item.Status.ACCEPTED and new_status == Item.Status.REJECTED:
                    from apps.points.models import PointsLedgerEntry
                    from apps.points.services import get_balance

                    award = (
                        PointsLedgerEntry.objects.filter(
                            reference_item=self.instance, entry_type=PointsLedgerEntry.EntryType.AWARD
                        )
                        .order_by("-created_at")
                        .first()
                    )
                    if award and get_balance(self.instance.user) < award.points:
                        self.add_error(
                            "status", "Cannot reverse this acceptance — the user has already spent these points."
                        )
        return cleaned


class ItemPhotoInline(admin.TabularInline):
    """Photos shown directly on their Item's page — ItemPhoto has its own
    unrelated UUID, so a separate top-level list gave no way to tell which
    photo belongs to which item."""
    model = ItemPhoto
    extra = 0
    readonly_fields = ("image_preview",)
    fields = ("image_preview", "image")

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:120px;">', obj.image.url)
        return "—"

    image_preview.short_description = "Preview"


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    form = ItemAdminForm
    list_display = ("id", "user", "category", "condition", "status", "created_at")
    list_filter = ("status", "category", "condition")
    search_fields = ("user__email", "user__username", "id")
    # Read-only, not editable: reassigning a submission to a different user
    # after the fact would desync points/dispatch history already
    # attributed to the original submitter.
    readonly_fields = ("user",)
    inlines = [ItemPhotoInline]

    def save_model(self, request, obj, form, change):
        # A plain save() here would skip transition_item_status entirely —
        # no state-machine check, no points award/reversal, no
        # notification. Route status changes through it instead; the form's
        # clean() already validated the transition is legal.
        if change and "status" in form.changed_data:
            fresh = Item.objects.get(pk=obj.pk)
            transition_item_status(fresh, obj.status, reason=obj.rejection_reason)
            other_changed = [f for f in ("category", "condition", "description") if f in form.changed_data]
            if other_changed:
                for field_name in other_changed:
                    setattr(fresh, field_name, getattr(obj, field_name))
                fresh.save(update_fields=other_changed + ["updated_at"])
            return
        super().save_model(request, obj, form, change)


admin.site.register(DriverAssignment)
