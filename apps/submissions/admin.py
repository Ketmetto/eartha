from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from rest_framework.exceptions import ValidationError
from unfold.admin import ModelAdmin, TabularInline
from .models import Item, ItemPhoto, DriverAssignment
from .services import transition_item_status
from .state_machine import can_transition


class ItemAdminForm(forms.ModelForm):
    """Validates a status change against the state machine at form-clean
    time, so an illegal edit re-renders the change form with a clear error
    instead of silently corrupting data (which is what a plain field save
    would otherwise do — see ItemAdmin.save_model)."""
    class Meta:
        model = Item
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        new_status = cleaned.get("status")
        if self.instance.pk and new_status:
            old_status = Item.objects.get(pk=self.instance.pk).status
            if new_status != old_status and not can_transition(old_status, new_status):
                self.add_error("status", f"Cannot move item from {old_status} to {new_status}.")
        return cleaned


class ItemPhotoInline(TabularInline):
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
class ItemAdmin(ModelAdmin):
    form = ItemAdminForm
    list_display = ("id", "user", "category", "condition", "status", "created_at")
    list_filter = ("status", "category", "condition")
    search_fields = ("user__email", "user__username", "id")
    # Read-only, not editable: reassigning a submission to a different user
    # after the fact would desync points/dispatch history already
    # attributed to the original submitter.
    readonly_fields = ("user",)
    inlines = [ItemPhotoInline]
    actions = ["award_points"]

    @admin.action(description="Award points (suggested amount, per condition)")
    def award_points(self, request, queryset):
        # Suggested-default only — free-text correction is the ops queue
        # web UI's job (apps/web/static/web/js/queue.js), this is a
        # convenience/fallback for the bulk case.
        from apps.points.rules import suggested_points
        from apps.points.services import set_item_award

        for item in queryset:
            try:
                set_item_award(item, suggested_points(item.condition), request.user)
            except ValidationError as e:
                self.message_user(request, f"Skipped {item.id}: {e}", level=messages.ERROR)

    def save_model(self, request, obj, form, change):
        # A plain save() here would skip transition_item_status entirely —
        # no state-machine check, no notification. Route status changes
        # through it instead; the form's clean() already validated the
        # transition is legal.
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


@admin.register(DriverAssignment)
class DriverAssignmentAdmin(ModelAdmin):
    pass
