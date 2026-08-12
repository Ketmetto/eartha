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


class ConfirmEmailChangePageView(TemplateView):
    template_name = "web/confirm-email-change.html"


class ResetPasswordPageView(TemplateView):
    template_name = "web/reset-password.html"


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


class UploadView(TemplateView):
    template_name = "web/upload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_maps_api_key"] = config("GOOGLE_MAPS_API_KEY", default="")
        return context
