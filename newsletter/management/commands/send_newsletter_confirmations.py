from datetime import timedelta
from urllib.parse import quote
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from newsletter.models import ConfirmationEmail
from newsletter.views import CONSENT, subscription_token


class Command(BaseCommand):
    help = 'Drain pending newsletter confirmations. Run once per minute; never sends campaigns.'

    def handle(self, *args, **options):
        sent = 0
        ids = list(ConfirmationEmail.objects.filter(sent_at=None, attempts__lt=3, created_at__gte=timezone.now()-timedelta(hours=48)).values_list('pk', flat=True)[:100])
        for pk in ids:
            with transaction.atomic():
                item = ConfirmationEmail.objects.select_for_update().select_related('subscriber').get(pk=pk)
                subscriber = item.subscriber
                if item.sent_at or item.attempts >= 3 or subscriber.status != 'pending' or item.token_version != subscriber.token_version:
                    continue
                item.attempts += 1
                base = settings.PUBLIC_SITE_URL.rstrip('/')
                confirm = f'{base}/newsletter/confirm#token={quote(subscription_token(subscriber, "confirm"))}'
                unsubscribe = f'{base}/newsletter/unsubscribe#token={quote(subscription_token(subscriber, "unsubscribe"))}'
                try:
                    send_mail('Confirm your TwinPeaks newsletter subscription',
                        f'Confirm your email to receive TwinPeaks articles and occasional service updates.\n\n{confirm}\n\nThis link expires in 48 hours.\n\nYour signup choice: {CONSENT}\n\nDid not request this? Ignore this email or cancel the request:\n{unsubscribe}',
                        settings.DEFAULT_FROM_EMAIL, [subscriber.email], fail_silently=False)
                except Exception:
                    item.failed = True
                    # Do not log addresses, credentials, tokens, or SMTP exception bodies.
                    self.stderr.write(f'Confirmation {item.pk} failed; attempt {item.attempts}/3.')
                else:
                    item.failed = False
                    item.sent_at = timezone.now()
                    sent += 1
                item.save()
        self.stdout.write(f'Sent {sent} confirmation email(s).')
