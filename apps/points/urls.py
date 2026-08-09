from django.urls import path
from .views import BalanceView, LedgerHistoryView, BenefitListView, RedeemBenefitView, MyRedemptionsView
from .admin_views import (
    BenefitAdminListCreateView, BenefitAdminDetailView, BenefitReorderView, ItemAwardView,
    PointsRuleAdminListView, PointsRuleBulkSaveView,
)

urlpatterns = [
    path("balance/", BalanceView.as_view(), name="points-balance"),
    path("history/", LedgerHistoryView.as_view(), name="points-history"),
    path("benefits/", BenefitListView.as_view(), name="benefits-list"),
    path("redeem/", RedeemBenefitView.as_view(), name="benefit-redeem"),
    path("redemptions/", MyRedemptionsView.as_view(), name="my-redemptions"),
    path("admin/benefits/", BenefitAdminListCreateView.as_view(), name="benefits-admin-list-create"),
    path("admin/benefits/reorder/", BenefitReorderView.as_view(), name="benefits-admin-reorder"),
    path("admin/benefits/<uuid:pk>/", BenefitAdminDetailView.as_view(), name="benefits-admin-detail"),
    path("admin/items/<uuid:pk>/award/", ItemAwardView.as_view(), name="items-admin-award"),
    path("admin/rules/", PointsRuleAdminListView.as_view(), name="points-rules-admin-list"),
    path("admin/rules/save/", PointsRuleBulkSaveView.as_view(), name="points-rules-admin-save"),
]
