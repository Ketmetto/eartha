from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import Order, OrderItem, Product, ProductImage
from .services import cancel_order


def _thumb(image, height=60):
    if image:
        return format_html('<img src="{}" style="max-height:{}px;">', image.url, height)
    return "—"


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("preview",)
    fields = ("preview", "image")

    def preview(self, obj):
        return _thumb(obj.image, 120)


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ("thumbnail", "name", "section", "price_usd", "size", "stock", "is_active", "display_order")
    list_display_links = ("thumbnail", "name")
    list_editable = ("price_usd", "stock", "is_active", "display_order")
    list_filter = ("section", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("preview",)
    fields = (
        "name", "section", "price_usd", "size", "description",
        "image", "preview", "stock", "is_active", "display_order",
    )
    inlines = [ProductImageInline]

    @admin.display(description="Photo")
    def thumbnail(self, obj):
        return _thumb(obj.image)

    @admin.display(description="Preview")
    def preview(self, obj):
        return _thumb(obj.image, 240)


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "unit_price_usd", "quantity")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

    def clean_status(self):
        new = self.cleaned_data["status"]
        if self.instance.pk:
            old = Order.objects.get(pk=self.instance.pk).status
            # Cancelling already returned the stock; reopening would need
            # to re-reserve it, which may no longer be possible.
            if old == Order.Status.CANCELLED and new != old:
                raise forms.ValidationError("A cancelled order can't be reopened — ask the customer to order again.")
        return new


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    form = OrderAdminForm
    list_display = ("number", "full_name", "phone", "city", "total_usd", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("full_name", "phone", "email", "id")
    readonly_fields = ("number", "total_usd", "created_at")
    fields = (
        "number", "status", "full_name", "phone", "email", "city", "address",
        "building", "floor_unit", "notes", "total_usd", "admin_notes", "created_at",
    )
    inlines = [OrderItemInline]
    actions = ["cancel_orders"]

    @admin.display(description="Order")
    def number(self, obj):
        return obj.number

    def save_model(self, request, obj, form, change):
        # Cancelling goes through cancel_order so the reserved stock is
        # returned; everything else is a plain field save.
        if change and "status" in form.changed_data and obj.status == Order.Status.CANCELLED:
            other = [f for f in form.changed_data if f != "status"]
            if other:
                Order.objects.filter(pk=obj.pk).update(**{f: getattr(obj, f) for f in other})
            cancel_order(obj)
            return
        super().save_model(request, obj, form, change)

    @admin.action(description="Cancel selected orders (returns stock)")
    def cancel_orders(self, request, queryset):
        for order in queryset:
            cancel_order(order)
        self.message_user(request, f"Cancelled {queryset.count()} order(s).", messages.SUCCESS)
