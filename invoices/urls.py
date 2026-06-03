from django.urls import path

from .views import (
    CustomerDetailView,
    CustomerListView,
    InvoiceDetailView,
    InvoiceGenerateView,
    InvoiceListView,
    InvoiceStatusUpdateView,
)


urlpatterns = [
    path("customers/", CustomerListView.as_view(), name="customer-list"),
    path("customers/<str:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path(
        "invoices/<int:pk>/status/",
        InvoiceStatusUpdateView.as_view(),
        name="invoice-status-update",
    ),
    path("invoices/generate/", InvoiceGenerateView.as_view(), name="invoice-generate"),
]
