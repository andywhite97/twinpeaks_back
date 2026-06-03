from django.urls import path

from .views import InvoiceDetailView, InvoiceGenerateView, InvoiceListView


urlpatterns = [
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/generate/", InvoiceGenerateView.as_view(), name="invoice-generate"),
]
