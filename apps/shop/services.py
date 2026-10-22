"""Order placement and cancellation — kept out of views so the stock
bookkeeping is in one place and testable."""
from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from base.form_guard import check_form_token, make_form_token
from notifications.tasks import send_transactional_email

from .models import Order, OrderItem, Product

ORDER_FORM_SALT = "shop.order-form"


def make_order_form_token():
    return make_form_token(ORDER_FORM_SALT)


def check_order_form_token(token):
    """See base.form_guard.check_form_token."""
    return check_form_token(token, ORDER_FORM_SALT)


def place_order(*, lines, **details) -> Order:
    """
    lines: [{"product": <uuid>, "quantity": int}, ...] from the client's
    basket. Prices always come from the database, never the client, and
    stock is checked and reserved under a row lock so two shoppers can't
    both buy the last piece. Raises DRF ValidationError (-> 400) naming
    the products that are no longer available.
    """
    quantities = {}
    for line in lines:
        quantities[line["product"]] = quantities.get(line["product"], 0) + line["quantity"]

    with transaction.atomic():
        products = {
            p.id: p
            for p in Product.objects.select_for_update().filter(id__in=quantities.keys(), is_active=True)
        }
        unavailable = [
            products[pid].name if pid in products else "an item"
            for pid, qty in quantities.items()
            if pid not in products or products[pid].stock < qty
        ]
        if unavailable:
            raise ValidationError(
                {"items": [f"No longer available in that quantity: {', '.join(unavailable)}. Update your basket and try again."]}
            )

        total = sum(products[pid].price_usd * qty for pid, qty in quantities.items())
        order = Order.objects.create(total_usd=total, **details)
        for pid, qty in quantities.items():
            product = products[pid]
            OrderItem.objects.create(
                order=order, product=product, product_name=product.name,
                unit_price_usd=product.price_usd, quantity=qty,
            )
            product.stock -= qty
            product.save(update_fields=["stock", "updated_at"])

    transaction.on_commit(lambda: notify_order_placed(order.id))
    return order


def cancel_order(order: Order):
    """Cancel and put the reserved stock back. Safe to call twice."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status == Order.Status.CANCELLED:
            return order
        for item in order.items.select_related("product"):
            if item.product_id:
                Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
    return order


# Forward-only, like the submissions pipeline: new → confirmed → delivered,
# with cancel allowed until delivery. Cancelled and delivered are final.
ORDER_TRANSITIONS = {
    Order.Status.NEW: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.DELIVERED, Order.Status.CANCELLED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}


def set_order_status(order: Order, new_status: str) -> Order:
    if new_status not in ORDER_TRANSITIONS[order.status]:
        raise ValidationError(
            {"status": f"Can't move an order from {order.get_status_display().lower()} to {Order.Status(new_status).label.lower()}."}
        )
    if new_status == Order.Status.CANCELLED:
        return cancel_order(order)
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return order


def replace_product_photos(product: Product, photos):
    """First photo becomes the main image, the rest extra images. Used on
    create, and on edit whenever new photos are chosen (they replace all
    the old ones — simpler for admins than per-photo management)."""
    from .models import ProductImage

    product.image = photos[0]
    product.save()
    product.extra_images.all().delete()
    for photo in photos[1:]:
        ProductImage.objects.create(product=product, image=photo)


def _order_summary(order):
    lines = [f"  {i.quantity} × {i.product_name} — ${i.line_total_usd:.2f}" for i in order.items.all()]
    return "\n".join(lines + [f"  Total: ${order.total_usd:.2f} (cash on delivery)"])


def notify_order_placed(order_id):
    order = Order.objects.prefetch_related("items").get(pk=order_id)
    address = ", ".join(x for x in [order.address, order.building, order.floor_unit, order.city] if x)
    send_transactional_email.delay(
        "info@eartha.me",
        f"New shop order {order.number}: ${order.total_usd:.2f}",
        "\n".join([
            f"{order.full_name}, {order.phone}" + (f", {order.email}" if order.email else ""),
            f"Deliver to: {address}",
            f"Notes: {order.notes}" if order.notes else "",
            "",
            _order_summary(order),
            "",
            f"Manage it here: {settings.SITE_URL}/admin/shop/order/{order.id}/change/",
        ]),
    )
    if order.email:
        send_transactional_email.delay(
            order.email,
            f"Your Eartha order {order.number}",
            "\n".join([
                f"Hi {order.full_name},",
                "",
                "Thank you for your order. We'll call you on "
                f"{order.phone} to confirm delivery. Payment is cash on delivery.",
                "",
                _order_summary(order),
                "",
                f"Delivering to: {address}",
                "",
                "— Eartha",
            ]),
        )
