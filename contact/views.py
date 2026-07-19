from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.throttling import AnonRateThrottle
from django.conf import settings
from .models import ContactMessage
from .serializers import ContactMessageSerializer

from bird import APIError, Bird


class ContactMessageCreateView(CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def perform_create(self, serializer):
        message = serializer.save()

        msg = ContactMessage.objects.get(pk=message.id)
        with Bird() as client:
            try:
                message = client.email.send(
                    from_={"email": "onboarding@messagebird.dev", "name": "Bird"},
                    to=["delivered@messagebird.dev", "andileblessinghlophe@gmail.com"],
                    subject=f"New Contact Message from {msg.name}",
                    html=f"<p>{msg.message}</p>",
                )
                print(message.id, message.status)
            except APIError as err:
                print("send failed:", err)


class ContactMessageListView(ListAPIView):
    queryset = ContactMessage.objects.all().order_by("-created_at")
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAdminUser]

