from decouple import config
from django.views.generic import TemplateView
from apps.content.services import get_site_texts, get_site_image_urls


class SiteContentMixin:
    """Adds site_texts/site_images to the template context — see
    apps.content.services. Only the marketing pages (index/about/contact)
    use this; every other page's copy/images are still hardcoded."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["site_texts"] = get_site_texts()
        context["site_images"] = get_site_image_urls()
        return context


class IndexView(SiteContentMixin, TemplateView):
    template_name = "web/index.html"


class AboutView(SiteContentMixin, TemplateView):
    template_name = "web/about.html"


class BenefitsView(TemplateView):
    template_name = "web/benefits.html"


class ContactView(SiteContentMixin, TemplateView):
    template_name = "web/contact.html"


class WishlistRequestView(TemplateView):
    """Public form for organizations — see WishlistRequestCreateView for
    the spam defenses the embedded form_token feeds into."""
    template_name = "web/wishlist-request.html"

    def get_context_data(self, **kwargs):
        from apps.engagement.services import make_wishlist_form_token

        context = super().get_context_data(**kwargs)
        context["form_token"] = make_wishlist_form_token()
        return context


class ShopView(SiteContentMixin, TemplateView):
    """Public Eartha Shop. Products are server-rendered per section; the
    same data goes to shop.js as JSON for the basket and detail view.
    Any section without a published, in-stock product shows "coming
    soon" — so does the whole page until the first product goes up."""
    template_name = "web/shop.html"

    def get_context_data(self, **kwargs):
        from apps.shop.models import Product
        from apps.shop.services import make_order_form_token

        context = super().get_context_data(**kwargs)
        products = list(
            Product.objects.filter(is_active=True, stock__gt=0).prefetch_related("extra_images")
        )
        context["sections"] = [
            {"key": key, "label": label, "products": [p for p in products if p.section == key]}
            for key, label in Product.Section.choices
        ]
        context["has_products"] = bool(products)
        context["products_json"] = [
            {
                "id": str(p.id),
                "name": p.name,
                "section": p.section,
                "price": f"{p.price_usd:.2f}",
                "size": p.size,
                "description": p.description,
                "stock": p.stock,
                "images": [p.image.url] + [i.image.url for i in p.extra_images.all()],
            }
            for p in products
        ]
        context["form_token"] = make_order_form_token()
        return context


class DashboardView(TemplateView):
    template_name = "web/dashboard.html"


class LoginView(TemplateView):
    template_name = "web/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["firebase_config"] = {
            "apiKey": config("FIREBASE_API_KEY", default=""),
            "authDomain": config("FIREBASE_AUTH_DOMAIN", default=""),
            "projectId": config("FIREBASE_PROJECT_ID", default=""),
            "appId": config("FIREBASE_APP_ID", default=""),
        }
        return context


class VerifyEmailPageView(TemplateView):
    template_name = "web/verify-email.html"


class NewsletterConfirmPageView(TemplateView):
    template_name = "web/newsletter-confirm.html"


class ConfirmEmailChangePageView(TemplateView):
    template_name = "web/confirm-email-change.html"


class ResetPasswordPageView(TemplateView):
    template_name = "web/reset-password.html"


class VoucherVerifyView(TemplateView):
    """Public, unauthenticated — the merchant-facing voucher check/redeem
    page a store employee lands on after scanning a customer's QR code."""
    template_name = "web/verify.html"


class ProfileView(TemplateView):
    template_name = "web/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_maps_api_key"] = config("GOOGLE_MAPS_API_KEY", default="")
        return context


class QueueView(TemplateView):
    template_name = "web/queue.html"


class UsersView(TemplateView):
    template_name = "web/users.html"


class ContentView(TemplateView):
    template_name = "web/content.html"


class ShopManageView(TemplateView):
    template_name = "web/shop-manage.html"


class TermsView(TemplateView):
    template_name = "web/terms.html"


class UploadView(TemplateView):
    template_name = "web/upload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_maps_api_key"] = config("GOOGLE_MAPS_API_KEY", default="")
        return context
