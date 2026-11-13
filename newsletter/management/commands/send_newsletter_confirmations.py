from datetime import timedelta
from bird import Bird
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from newsletter.models import ConfirmationEmail
from newsletter.emails import CONFIRMATION_SUBJECT, confirmation_email


class Command(BaseCommand):
    help = 'Drain pending newsletter confirmations. Run once per minute; never sends campaigns.'

    def add_arguments(self, parser):
        parser.add_argument('--recipient', help='Limit delivery to one email address for an operational test.')

    def handle(self, *args, **options):
        sent = 0
        pending = ConfirmationEmail.objects.filter(sent_at=None, attempts__lt=3, created_at__gte=timezone.now()-timedelta(hours=48))
        if options.get('recipient'):
            pending = pending.filter(subscriber__email=options['recipient'].strip().lower())
        ids = list(pending.order_by('pk').values_list('pk', flat=True)[:100])
        for pk in ids:
            with transaction.atomic():
                item = ConfirmationEmail.objects.select_for_update().select_related('subscriber').get(pk=pk)
                subscriber = item.subscriber
                if item.sent_at or item.attempts >= 3 or subscriber.status != 'pending' or item.token_version != subscriber.token_version:
                    continue
                item.attempts += 1
                try:
                    html, text = confirmation_email(subscriber)
                    provider = settings.NEWSLETTER_EMAIL_PROVIDER
                    if provider == 'bird':
                        if not settings.BIRD_API_KEY:
                            raise ImproperlyConfigured('BIRD_API_KEY is required')
                        with Bird(api_key=settings.BIRD_API_KEY, timeout=20, max_retries=0) as client:
                            client.email.send(
                                from_={'email': settings.CONTACT_FROM_EMAIL, 'name': settings.CONTACT_FROM_NAME},
                                to=[subscriber.email], subject=CONFIRMATION_SUBJECT,
                                html=html, text=text, track_clicks=False, track_opens=False)
                    elif provider == 'django':
                        accepted = send_mail(CONFIRMATION_SUBJECT, text,
                            settings.DEFAULT_FROM_EMAIL, [subscriber.email], fail_silently=False, html_message=html)
                        if accepted != 1:
                            raise RuntimeError('Email backend did not accept the confirmation')
                    else:
                        raise ImproperlyConfigured('Unknown newsletter email provider')
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
