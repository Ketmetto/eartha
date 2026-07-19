from django.urls import path
from .views import ItemUploadView
from .admin_views import (
    SubmissionReviewQueueView,
    SubmissionDecisionView,
    DriverDispatchView,
)

urlpatterns = [
    path("", ItemUploadView.as_view(), name="submissions-list-create"),
    path("admin/queue/", SubmissionReviewQueueView.as_view(), name="submissions-admin-queue"),
    path("admin/<uuid:pk>/decision/", SubmissionDecisionView.as_view(), name="submissions-admin-decision"),
    path("admin/<uuid:pk>/dispatch/", DriverDispatchView.as_view(), name="submissions-admin-dispatch"),
]
