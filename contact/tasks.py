import os

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

from .models import ContactMessage
from bird import APIError, Bird


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 30})
def send_contact_message_notification(self, message_id):
    msg = ContactMessage.objects.get(pk=message_id)
    with Bird(api_key=settings.BIRD_API_KEY) as client:
        try:
            message = client.email.send(
                from_={"email": "onboarding@messagebird.dev", "name": "Bird"},
                to=["delivered@messagebird.dev", "andileblessinghlophe@gmail.com"],
                subject=f"New Contact Message from {msg.name}",
                html=msg.message,
            )
            print(message.id, message.status)
        except APIError as err:
            print("send failed:", err)