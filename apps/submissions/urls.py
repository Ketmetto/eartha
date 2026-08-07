from django.urls import path
from .views import ItemUploadView
from .admin_views import (
    SubmissionReviewQueueView,
    SubmissionAdminListView,
    SubmissionAdminDoneListView,
    SubmissionDecisionView,
    DriverAdminListCreateView,
    DriverAdminDetailView,
    DriverDispatchView,
    DriverReassignView,
    SubmissionMarkCollectedView,
    SubmissionMarkCompletedView,
)

urlpatterns = [
    path("", ItemUploadView.as_view(), name="submissions-list-create"),
    path("admin/queue/", SubmissionReviewQueueView.as_view(), name="submissions-admin-queue"),
    path("admin/action/", SubmissionAdminListView.as_view(), name="submissions-admin-action"),
    path("admin/done/", SubmissionAdminDoneListView.as_view(), name="submissions-admin-done"),
    path("admin/<uuid:pk>/decision/", SubmissionDecisionView.as_view(), name="submissions-admin-decision"),
    path("admin/drivers/", DriverAdminListCreateView.as_view(), name="submissions-admin-drivers"),
    path("admin/drivers/<uuid:pk>/", DriverAdminDetailView.as_view(), name="submissions-admin-driver-detail"),
    path("admin/<uuid:pk>/dispatch/", DriverDispatchView.as_view(), name="submissions-admin-dispatch"),
    path("admin/<uuid:pk>/reassign-driver/", DriverReassignView.as_view(), name="submissions-admin-reassign-driver"),
    path("admin/<uuid:pk>/collect/", SubmissionMarkCollectedView.as_view(), name="submissions-admin-collect"),
    path("admin/<uuid:pk>/complete/", SubmissionMarkCompletedView.as_view(), name="submissions-admin-complete"),
]
