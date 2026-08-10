from django.urls import path
from .admin_views import (
    SiteTextAdminListView,
    SiteTextAdminUpdateView,
    SiteImageAdminListView,
    SiteImageAdminUpdateView,
    SiteImageAdminClearView,
)

urlpatterns = [
    path("admin/texts/", SiteTextAdminListView.as_view(), name="content-admin-texts"),
    path("admin/texts/<str:key>/", SiteTextAdminUpdateView.as_view(), name="content-admin-text-detail"),
    path("admin/images/", SiteImageAdminListView.as_view(), name="content-admin-images"),
    path("admin/images/<str:key>/", SiteImageAdminUpdateView.as_view(), name="content-admin-image-detail"),
    path("admin/images/<str:key>/clear/", SiteImageAdminClearView.as_view(), name="content-admin-image-clear"),
]
