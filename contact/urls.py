from django.urls import path
from .views import ContactMessageCreateView, ContactMessageListView

urlpatterns = [
    path("contact/", ContactMessageCreateView.as_view(), name="contact-create"),
    path("contact/messages/", ContactMessageListView.as_view(), name="contact-list"),
]
