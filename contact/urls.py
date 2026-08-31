from django.urls import path
from .views import ContactMessageCreateView, ContactMessageListView, PublicQuotationDecisionView, PublicQuotationPdfView, PublicQuotationView, QuotationRequestCreateView

urlpatterns = [
    path("contact/", ContactMessageCreateView.as_view(), name="contact-create"),
    path("contact/messages/", ContactMessageListView.as_view(), name="contact-list"),
    path("quotations/", QuotationRequestCreateView.as_view(), name="quotation-request-create"),
    path("quotations/public/<uuid:token>/", PublicQuotationView.as_view(), name="quotation-public"),
    path("quotations/public/<uuid:token>/pdf/", PublicQuotationPdfView.as_view(), name="quotation-pdf"),
    path("quotations/public/<uuid:token>/accept/", PublicQuotationDecisionView.as_view(), {"decision": "accept"}, name="quotation-accept"),
    path("quotations/public/<uuid:token>/decline/", PublicQuotationDecisionView.as_view(), {"decision": "decline"}, name="quotation-decline"),
]
