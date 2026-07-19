from django.urls import path
from .views import BalanceView, LedgerHistoryView, BenefitListView, RedeemBenefitView

urlpatterns = [
    path("balance/", BalanceView.as_view(), name="points-balance"),
    path("history/", LedgerHistoryView.as_view(), name="points-history"),
    path("benefits/", BenefitListView.as_view(), name="benefits-list"),
    path("redeem/", RedeemBenefitView.as_view(), name="benefit-redeem"),
]
