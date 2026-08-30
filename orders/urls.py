from django.urls import path

from .views import MomoCheckoutView, MomoPaymentStatusView

urlpatterns = [
    path("checkout/momo/", MomoCheckoutView.as_view(), name="momo-checkout"),
    path("checkout/momo/<uuid:reference_id>/", MomoPaymentStatusView.as_view(), name="momo-payment-status"),
]
