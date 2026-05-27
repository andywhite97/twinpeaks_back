from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.throttling import AnonRateThrottle
from .models import ContactMessage
from .serializers import ContactMessageSerializer
from django.core.mail import send_mail
from django.conf import settings


class ContactMessageCreateView(CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def perform_create(self, serializer):
        message = serializer.save()
        print(message)
        
        send_mail(
            subject=f"New Contact Message from {message.name}",
            message=message.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['andileblessinghlophe@gmail.com'],
            fail_silently=False,
        )


class ContactMessageListView(ListAPIView):
    queryset = ContactMessage.objects.all().order_by("-created_at")
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAdminUser]

