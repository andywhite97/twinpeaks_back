from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.throttling import AnonRateThrottle
from django.conf import settings
from .models import ContactMessage
from .serializers import ContactMessageSerializer
from .tasks import send_contact_message_notification


class ContactMessageCreateView(CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def perform_create(self, serializer):
        message = serializer.save()

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            send_contact_message_notification.apply(args=(message.id,))
        else:
            send_contact_message_notification.delay(message.id)


class ContactMessageListView(ListAPIView):
    queryset = ContactMessage.objects.all().order_by("-created_at")
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAdminUser]

