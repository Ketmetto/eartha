from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/submissions/", include("apps.submissions.urls")),
    path("api/v1/points/", include("apps.points.urls")),
    path("api/v1/engagement/", include("apps.engagement.urls")),
    path("api/v1/content/", include("apps.content.urls")),
    path("", include("apps.web.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
