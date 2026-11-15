from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from newsletter.models import ConfirmationEmail
from newsletter.delivery import send_confirmation


class Command(BaseCommand):
    help = 'Retry pending newsletter confirmations; never sends campaigns.'

    def add_arguments(self, parser):
        parser.add_argument('--recipient', help='Limit delivery to one email address for an operational test.')

    def handle(self, *args, **options):
        pending = ConfirmationEmail.objects.filter(sent_at=None, attempts__lt=3, created_at__gte=timezone.now()-timedelta(hours=48))
        if options.get('recipient'):
            pending = pending.filter(subscriber__email=options['recipient'].strip().lower())
        ids = list(pending.order_by('pk').values_list('pk', flat=True)[:100])
        sent = sum(send_confirmation(pk) for pk in ids)
        self.stdout.write(f'Sent {sent} confirmation email(s).')
