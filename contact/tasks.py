import os

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

from .models import ContactMessage


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 30})
def send_contact_message_notification(self, message_id):
    message = ContactMessage.objects.get(pk=message_id)
    send_mail(
        subject=f"New Contact Message from {message.name}",
        message=message.message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[os.getenv('CONTACT_NOTIFICATION_EMAIL', 'andileblessinghlophe@gmail.com')],
        fail_silently=False,
    )
