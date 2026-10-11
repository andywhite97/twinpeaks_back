from django.core.management.base import BaseCommand

from orders.models import Payment
from orders.momo import MomoCollectionClient, MomoConfigurationError, MomoRequestError
from orders.reconciliation import reconcile_payment


class Command(BaseCommand):
    help = 'List pending MoMo references; --apply queries existing provider payments and reconciles them. Never initiates a charge.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        if options['limit'] < 1:
            self.stderr.write('--limit must be positive.')
            return
        payments = Payment.objects.filter(status=Payment.Status.PENDING).order_by('created_at')[:options['limit']]
        for payment in payments:
            if not options['apply']:
                self.stdout.write(f'{payment.reference_id}: pending (no provider request)')
                continue
            try:
                data = MomoCollectionClient().get_status(payment.reference_id)
                order = reconcile_payment(payment, data)
                self.stdout.write(f'{payment.reference_id}: {order.status}')
            except (MomoConfigurationError, MomoRequestError, ValueError):
                self.stderr.write(f'{payment.reference_id}: status unavailable; payment unchanged')
