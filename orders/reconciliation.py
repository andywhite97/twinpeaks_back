from collections import Counter
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F

from products.models import Product
from .models import Order, Payment


class InventoryAllocationConflict(Exception):
    pass


def reconcile_payment(payment, provider_data):
    """Provider I/O happens before this function; all state changes share one lock order.

    SUCCESSFUL is the durable provider-success marker, including manual-review
    orders. It must never be reverted by a stale pending/failed response.
    """
    provider_status = str(provider_data.get('status', '')).upper()
    if provider_status not in {'SUCCESSFUL', 'FAILED', 'REJECTED', 'TIMEOUT', 'PENDING'}:
        raise ValueError('Unknown payment-provider status.')

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=payment.order_id)
        locked_payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if locked_payment.status == Payment.Status.SUCCESSFUL:
            return order
        if locked_payment.status == Payment.Status.FAILED and provider_status != 'SUCCESSFUL':
            return order

        previous_provider_status = locked_payment.provider_status
        locked_payment.provider_status = provider_status
        locked_payment.provider_transaction_id = str(provider_data.get('financialTransactionId', ''))[:100]
        if provider_status == 'SUCCESSFUL':
            # Aggregate repeated products, including historical/admin-created lines.
            required = Counter()
            items = list(order.items.order_by('pk'))
            valid_lines = bool(items) and all(item.product_id and item.quantity > 0 for item in items)
            for item in items:
                if item.product_id:
                    required[item.product_id] += item.quantity
            # Lock actual product rows, not an outer join to nullable products.
            products = {product.pk: product for product in Product.objects.select_for_update()
                        .filter(pk__in=required).order_by('pk')}
            can_allocate = valid_lines and all(
                product_id in products and products[product_id].stock_quantity >= quantity
                for product_id, quantity in required.items()
            )
            # Compare provider totals when returned, without trusting client totals.
            try:
                if 'amount' in provider_data and Decimal(str(provider_data['amount'])) != locked_payment.amount:
                    can_allocate = False
            except InvalidOperation:
                can_allocate = False
            if 'currency' in provider_data and provider_data['currency'] != locked_payment.currency:
                can_allocate = False
            # Existing review/paid/cancelled records may contain legacy partial
            # allocations. Never attempt a second automatic allocation on them.
            safe_order = order.status in {Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_FAILED}
            if order.status == Order.Status.PAYMENT_REVIEW and previous_provider_status in {'REQUESTING', 'REQUEST_UNKNOWN'}:
                safe_order = True  # Newly persisted request; no allocation has taken place.
            if can_allocate and safe_order:
                try:
                    # Savepoint protects against any unexpected conditional-update conflict.
                    with transaction.atomic():
                        for product_id, quantity in sorted(required.items()):
                            updated = Product.objects.filter(pk=product_id, stock_quantity__gte=quantity).update(
                                stock_quantity=F('stock_quantity') - quantity)
                            if updated != 1:
                                raise InventoryAllocationConflict()
                    order.status = Order.Status.PAID
                except InventoryAllocationConflict:
                    order.status = Order.Status.PAYMENT_REVIEW
            else:
                order.status = Order.Status.PAYMENT_REVIEW
            locked_payment.status = Payment.Status.SUCCESSFUL
        elif provider_status in {'FAILED', 'REJECTED', 'TIMEOUT'}:
            locked_payment.status = Payment.Status.FAILED
            if order.status in {Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_FAILED} or (
                order.status == Order.Status.PAYMENT_REVIEW and previous_provider_status in {'REQUESTING', 'REQUEST_UNKNOWN'}
            ):
                order.status = Order.Status.PAYMENT_FAILED
        # Preserve REQUEST_UNKNOWN while pending so eventual success can allocate.
        elif previous_provider_status in {'REQUESTING', 'REQUEST_UNKNOWN'}:
            locked_payment.provider_status = previous_provider_status

        locked_payment.save(update_fields=['status', 'provider_status', 'provider_transaction_id', 'updated_at'])
        order.save(update_fields=['status', 'updated_at'])
        return order
