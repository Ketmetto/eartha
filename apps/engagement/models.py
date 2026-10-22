from django.db import models
from base.models import BaseModel


class ContactMessage(BaseModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    is_partner_inquiry = models.BooleanField(default=False)
    resolved = models.BooleanField(default=False)


class ImpactStat(BaseModel):
    """Single row, admin-editable, powers the public 'About us' impact numbers.
    partner_brands_count isn't a field here — it's computed live from active
    Benefit rows in ImpactStatSerializer, so it can't drift from what the
    Benefits page actually shows."""
    items_collected = models.PositiveIntegerField(default=0)
    co2_saved_kg = models.PositiveIntegerField(default=0)


class NewsletterSubscriber(BaseModel):
    """Homepage newsletter signups. Kept in our own DB as the source of
    truth — export to CSV from the admin to import into Brevo (or any
    other campaign tool) when a newsletter actually goes out. Double
    opt-in: an address only counts once confirmed_at is set, via the
    emailed link (see services.confirm_newsletter_subscription)."""
    email = models.EmailField(unique=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)


class WishlistRequest(BaseModel):
    """A clothing need shared by an organization through the public
    Eartha Wishlist form. No account required — spam is handled at the
    view (throttle + honeypot + signed page-load token, see
    services.check_wishlist_form_token), and every request is reviewed by
    an admin before anything is matched against it."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        MATCHED = "matched", "Matched"
        FULFILLED = "fulfilled", "Fulfilled"
        DECLINED = "declined", "Declined"

    organization = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    items_needed = models.TextField()
    sizes = models.CharField(max_length=200, blank=True)
    quantity = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    needed_by = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.organization} — {self.created_at:%Y-%m-%d}" if self.created_at else self.organization
