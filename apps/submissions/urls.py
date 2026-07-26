from django.urls import path
from .views import ItemUploadView
from .admin_views import (
    SubmissionReviewQueueView,
    SubmissionAdminListView,
    SubmissionDecisionView,
    DriverDispatchView,
    SubmissionMarkCollectedView,
    SubmissionMarkCompletedView,
)

urlpatterns = [
    path("", ItemUploadView.as_view(), name="submissions-list-create"),
    path("admin/queue/", SubmissionReviewQueueView.as_view(), name="submissions-admin-queue"),
    path("admin/all/", SubmissionAdminListView.as_view(), name="submissions-admin-all"),
    path("admin/<uuid:pk>/decision/", SubmissionDecisionView.as_view(), name="submissions-admin-decision"),
    path("admin/<uuid:pk>/dispatch/", DriverDispatchView.as_view(), name="submissions-admin-dispatch"),
    path("admin/<uuid:pk>/collect/", SubmissionMarkCollectedView.as_view(), name="submissions-admin-collect"),
    path("admin/<uuid:pk>/complete/", SubmissionMarkCompletedView.as_view(), name="submissions-admin-complete"),
]
