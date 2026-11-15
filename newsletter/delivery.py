"""Immediate confirmation delivery, also used by the manual retry command."""
import logging
from datetime import timedelta

from bird import Bird
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .emails import CONFIRMATION_SUBJECT, confirmation_email
from .models import ConfirmationEmail, Subscriber

logger = logging.getLogger(__name__)


def send_confirmation(pk):
    with transaction.atomic():
        # Match the signup lock order, and serialize against confirm/unsubscribe.
        subscriber_id = ConfirmationEmail.objects.values_list('subscriber_id', flat=True).get(pk=pk)
        subscriber = Subscriber.objects.select_for_update().get(pk=subscriber_id)
        item = ConfirmationEmail.objects.select_for_update().get(pk=pk)
        cutoff = timezone.now() - timedelta(hours=48)
        if (item.sent_at or item.attempts >= 3 or subscriber.status != 'pending'
                or item.token_version != subscriber.token_version
                or item.created_at < cutoff or subscriber.requested_at < cutoff):
            return False
        item.attempts += 1
        try:
            html, text = confirmation_email(subscriber)
            if settings.NEWSLETTER_EMAIL_PROVIDER == 'bird':
                if not settings.BIRD_API_KEY:
                    raise ImproperlyConfigured('BIRD_API_KEY is required')
                with Bird(api_key=settings.BIRD_API_KEY, timeout=20, max_retries=0) as client:
                    client.email.send(
                        from_={'email': settings.CONTACT_FROM_EMAIL, 'name': settings.CONTACT_FROM_NAME},
                        to=[subscriber.email], subject=CONFIRMATION_SUBJECT,
                        html=html, text=text, track_clicks=False, track_opens=False)
            elif settings.NEWSLETTER_EMAIL_PROVIDER == 'django':
                accepted = send_mail(CONFIRMATION_SUBJECT, text,
                    settings.DEFAULT_FROM_EMAIL, [subscriber.email], fail_silently=False, html_message=html)
                if accepted != 1:
                    raise RuntimeError('Email backend did not accept the confirmation')
            else:
                raise ImproperlyConfigured('Unknown newsletter email provider')
        except Exception:
            item.failed = True
            # Never log provider exceptions, addresses, tokens or credentials.
            logger.warning('Confirmation %s failed; attempt %s/3.', item.pk, item.attempts)
        else:
            item.failed = False
            item.sent_at = timezone.now()
        item.save(update_fields=['attempts', 'failed', 'sent_at'])
        return item.sent_at is not None
