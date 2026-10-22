from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from base.models import BaseModel
from base.validators import validate_image_content_type, validate_image_size


class Product(BaseModel):
    """A piece for sale in the Eartha Shop. Managed entirely from the
    Django admin; the public /shop/ page lists every active, in-stock
    product and shows "coming soon" for any section with none."""

    class Section(models.TextChoices):
        MEN = "men", "Men"
        WOMEN = "women", "Women"
        KIDS = "kids", "Kids"

    name = models.CharField(max_length=120)
    section = models.CharField(max_length=10, choices=Section.choices, db_index=True)
    price_usd = models.DecimalField(
        "Price (USD)", max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    size = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="shop/", validators=[validate_image_size, validate_image_content_type])
    # Most pieces are one-offs (stock 1); placing an order reserves stock
    # straight away, so the same piece can't be sold twice while an order
    # waits for cash-on-delivery. Cancelling the order puts it back.
    stock = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField("Published", default=True)
    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")

    class Meta(BaseModel.Meta):
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return f"{self.name} (${self.price_usd})"


class ProductImage(BaseModel):
    """Extra photos beyond the main one, shown on the product's detail view."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="extra_images")
    image = models.ImageField(upload_to="shop/", validators=[validate_image_size, validate_image_content_type])

    class Meta(BaseModel.Meta):
        ordering = ["created_at"]


class Order(BaseModel):
    """A cash-on-delivery order. No account needed — the contact and
    delivery details are captured on the order itself."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONFIRMED = "confirmed", "Confirmed"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    building = models.CharField(max_length=120, blank=True)
    floor_unit = models.CharField(max_length=60, blank=True)
    notes = models.TextField(blank=True)
    total_usd = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    admin_notes = models.TextField(blank=True)

    @property
    def number(self):
        """Short reference shown to the customer and in emails."""
        return str(self.id)[:8].upper()

    def __str__(self):
        return f"Order {self.number} — {self.full_name}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # SET_NULL + the snapshots below: deleting a product later mustn't
    # erase what was actually sold, or at what price.
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name="+")
    product_name = models.CharField(max_length=120)
    unit_price_usd = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta(BaseModel.Meta):
        ordering = ["created_at"]

    @property
    def line_total_usd(self):
        return self.unit_price_usd * self.quantity
