from django.urls import path

from .admin_views import (
    NewOrderCountView,
    OrderAdminListView,
    OrderStatusView,
    ProductAdminDetailView,
    ProductAdminListCreateView,
)
from .views import OrderCreateView

urlpatterns = [
    path("orders/", OrderCreateView.as_view(), name="shop-order-create"),
    path("admin/products/", ProductAdminListCreateView.as_view(), name="shop-admin-products"),
    path("admin/products/<uuid:pk>/", ProductAdminDetailView.as_view(), name="shop-admin-product-detail"),
    path("admin/orders/", OrderAdminListView.as_view(), name="shop-admin-orders"),
    path("admin/orders/new-count/", NewOrderCountView.as_view(), name="shop-admin-new-order-count"),
    path("admin/orders/<uuid:pk>/status/", OrderStatusView.as_view(), name="shop-admin-order-status"),
]
