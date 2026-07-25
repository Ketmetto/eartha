from decouple import config
from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = "web/index.html"


class AboutView(TemplateView):
    template_name = "web/about.html"


class BenefitsView(TemplateView):
    template_name = "web/benefits.html"


class ContactView(TemplateView):
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


class ProfileView(TemplateView):
    template_name = "web/profile.html"


class QueueView(TemplateView):
    template_name = "web/queue.html"


class UploadView(TemplateView):
    template_name = "web/upload.html"
