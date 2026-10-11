from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import StringIO
from threading import Barrier
import uuid
from unittest.mock import Mock, patch

import requests
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.test import APIClient

from products.models import Product
from .models import Order, OrderItem, Payment
from .momo import MomoCollectionClient, MomoRequestError
from .reconciliation import reconcile_payment


def make_payment(products, *, order_status=Order.Status.PENDING_PAYMENT, provider_status=''):
    order = Order.objects.create(customer_name='Buyer', email='buyer@example.com', phone_number='26876123456',
        subtotal=Decimal('20'), currency='EUR', status=order_status)
    for product, quantity in products:
        OrderItem.objects.create(order=order, product=product, product_name=product.name,
            product_slug=product.slug, unit_price=Decimal('10'), quantity=quantity, line_total=Decimal('10') * quantity)
    return Payment.objects.create(order=order, reference_id=uuid.uuid4(), amount=order.subtotal,
        currency='EUR', provider_status=provider_status)


class ReconciliationTests(TestCase):
    def setUp(self):
        self.a = Product.objects.create(name='Camera', slug='camera', price='10', stock_quantity=3)
        self.b = Product.objects.create(name='Router', slug='router', price='10', stock_quantity=0)

    def stock(self, product):
        product.refresh_from_db()
        return product.stock_quantity

    def test_later_unavailable_line_deducts_nothing_and_success_review_is_terminal(self):
        payment = make_payment([(self.a, 2), (self.b, 1)])
        order = reconcile_payment(payment, {'status': 'SUCCESSFUL'})
        self.assertEqual(order.status, Order.Status.PAYMENT_REVIEW)
        self.assertEqual(self.stock(self.a), 3)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESSFUL)
        self.b.stock_quantity = 3
        self.b.save()
        reconcile_payment(payment, {'status': 'SUCCESSFUL'})
        self.assertEqual(self.stock(self.a), 3)
        self.assertEqual(self.stock(self.b), 3)

    def test_success_cannot_be_deducted_twice_or_downgraded_by_stale_status(self):
        payment = make_payment([(self.a, 2)])
        for provider_status in ('SUCCESSFUL', 'SUCCESSFUL', 'FAILED', 'PENDING'):
            order = reconcile_payment(payment, {'status': provider_status})
            self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(self.stock(self.a), 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESSFUL)

    def test_aggregate_duplicate_lines_before_allocating(self):
        payment = make_payment([(self.a, 2), (self.a, 2)])
        self.assertEqual(reconcile_payment(payment, {'status': 'SUCCESSFUL'}).status, Order.Status.PAYMENT_REVIEW)
        self.assertEqual(self.stock(self.a), 3)

    def test_conditional_conflict_rolls_back_all_previous_deductions(self):
        self.b.stock_quantity = 3
        self.b.save()
        payment = make_payment([(self.a, 1), (self.b, 1)])
        original_update = QuerySet.update
        allocations = []

        def conflicting_update(queryset, **kwargs):
            if 'stock_quantity' in kwargs:
                allocations.append(True)
                if len(allocations) == 2:
                    return 0
            return original_update(queryset, **kwargs)

        with patch.object(QuerySet, 'update', conflicting_update):
            order = reconcile_payment(payment, {'status': 'SUCCESSFUL'})
        self.assertEqual(order.status, Order.Status.PAYMENT_REVIEW)
        self.assertEqual(self.stock(self.a), 3)
        self.assertEqual(self.stock(self.b), 3)

    def test_deleted_product_and_legacy_review_never_allocate(self):
        for status in (Order.Status.PAYMENT_REVIEW, Order.Status.CANCELLED):
            payment = make_payment([(self.a, 1)], order_status=status)
            self.assertEqual(reconcile_payment(payment, {'status': 'SUCCESSFUL'}).status, Order.Status.PAYMENT_REVIEW)
        payment = make_payment([(self.b, 1)])
        self.b.delete()
        self.assertEqual(reconcile_payment(payment, {'status': 'SUCCESSFUL'}).status, Order.Status.PAYMENT_REVIEW)
        self.assertEqual(self.stock(self.a), 3)

    def test_ambiguous_request_pending_then_success_allocates_once(self):
        payment = make_payment([(self.a, 1)], order_status=Order.Status.PAYMENT_REVIEW, provider_status='REQUEST_UNKNOWN')
        reconcile_payment(payment, {'status': 'PENDING'})
        order = reconcile_payment(payment, {'status': 'SUCCESSFUL'})
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(self.stock(self.a), 2)

    def test_failure_then_late_success_and_unknown_response(self):
        payment = make_payment([(self.a, 1)])
        reconcile_payment(payment, {'status': 'FAILED'})
        self.assertEqual(reconcile_payment(payment, {'status': 'PENDING'}).status, Order.Status.PAYMENT_FAILED)
        self.assertEqual(reconcile_payment(payment, {'status': 'SUCCESSFUL'}).status, Order.Status.PAID)
        with self.assertRaises(ValueError):
            reconcile_payment(payment, {'status': 'UNKNOWN'})

    def test_provider_total_mismatch_requires_review_without_deduction(self):
        for fields in ({'amount': '999'}, {'amount': 'invalid'}, {'currency': 'USD'}):
            payment = make_payment([(self.a, 1)])
            self.assertEqual(reconcile_payment(payment, {'status': 'SUCCESSFUL', **fields}).status,
                Order.Status.PAYMENT_REVIEW)
        self.assertEqual(self.stock(self.a), 3)

    @patch('orders.management.commands.reconcile_momo.MomoCollectionClient')
    def test_management_command_defaults_to_no_network_and_apply_only_checks_existing(self, client):
        payment = make_payment([(self.a, 1)])
        call_command('reconcile_momo', stdout=StringIO())
        client.assert_not_called()
        client.return_value.get_status.return_value = {'status': 'SUCCESSFUL'}
        call_command('reconcile_momo', apply=True, stdout=StringIO())
        client.return_value.get_status.assert_called_once_with(payment.reference_id)
        client.return_value.request_to_pay.assert_not_called()
        self.assertEqual(self.stock(self.a), 2)


@override_settings(SHOP_CURRENCY='EUR', MOMO_CURRENCY='EUR', MOMO_COLLECTION_SUBSCRIPTION_KEY='test',
    MOMO_COLLECTION_API_USER='test', MOMO_COLLECTION_API_KEY='test')
class CheckoutRecoveryTests(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(name='Camera', slug='camera', price='10', stock_quantity=3)
        self.data = {'customer_name': 'Buyer', 'email': 'buyer@example.com', 'phone_number': '26876123456',
            'meta_event_id': str(uuid.uuid4()), 'items': [{'product_id': self.product.pk, 'quantity': 1}]}
        self.notification = patch('orders.views.send_order_placement_notification').start()
        self.addCleanup(patch.stopall)

    @patch('orders.momo.requests.post')
    def test_timeout_persists_reference_without_locks_and_replay_does_not_charge(self, post):
        token = Mock(ok=True)
        token.json.return_value = {'access_token': 'test'}

        def provider_call(*args, **kwargs):
            self.assertFalse(connection.in_atomic_block)
            self.assertEqual(Payment.objects.count(), 1)
            if args[0].endswith('/token/'):
                return token
            self.assertEqual(kwargs['headers']['X-Reference-Id'], str(Payment.objects.get().reference_id))
            raise requests.Timeout()

        post.side_effect = provider_call
        response = self.client.post('/api/checkout/momo/', self.data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['order_status'], 'payment_review')
        self.assertEqual(response.data['payment_status'], 'pending')
        reference = response.data['payment_reference']
        self.assertEqual(self.client.post('/api/checkout/momo/', self.data, format='json').data['payment_reference'], reference)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.data['items'][0]['quantity'] = 2
        self.assertEqual(self.client.post('/api/checkout/momo/', self.data, format='json').status_code, 409)

    @patch('orders.momo.requests.post')
    def test_definitive_rejection_is_not_pending_and_token_errors_are_normalized(self, post):
        token = Mock(ok=True)
        token.json.return_value = {'access_token': 'test'}
        post.side_effect = [token, Mock(status_code=400)]
        response = self.client.post('/api/checkout/momo/', self.data, format='json')
        self.assertEqual(response.data['payment_status'], 'failed')
        post.side_effect = requests.Timeout()
        with self.assertRaises(MomoRequestError):
            MomoCollectionClient().get_status(uuid.uuid4())

    @patch('orders.momo.requests.get')
    @patch('orders.momo.requests.post')
    def test_status_timeout_and_malformed_response_leave_payment_unchanged(self, post, get):
        payment = make_payment([(self.product, 1)])
        token = Mock(ok=True)
        token.json.return_value = {'access_token': 'test'}
        post.return_value = token
        get.side_effect = requests.Timeout()
        self.assertEqual(self.client.get(f'/api/checkout/momo/{payment.reference_id}/').status_code, 503)
        get.side_effect = None
        malformed = Mock(ok=True)
        malformed.json.return_value = {'status': 'NOT_A_STATE'}
        get.return_value = malformed
        self.assertEqual(self.client.get(f'/api/checkout/momo/{payment.reference_id}/').status_code, 503)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

    def test_private_event_source_rejected_and_public_query_removed(self):
        self.data['event_source_url'] = 'https://twinpeaksinvestment.com/quotations/private-token'
        self.assertEqual(self.client.post('/api/checkout/momo/', self.data, format='json').status_code, 400)
        from .serializers import CheckoutSerializer
        self.data['event_source_url'] = 'https://twinpeaksinvestment.com/cart?email=buyer@example.com#private'
        serializer = CheckoutSerializer(data=self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['event_source_url'], 'https://twinpeaksinvestment.com/cart')


class DatabaseConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Camera', slug='camera', price='10', stock_quantity=3)

    def concurrently(self, payments):
        barrier = Barrier(2)

        def worker(pk):
            close_old_connections()
            try:
                payment = Payment.objects.get(pk=pk)
                barrier.wait(timeout=10)
                return reconcile_payment(payment, {'status': 'SUCCESSFUL'}).status
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, payment.pk) for payment in payments]
            return [future.result(timeout=20) for future in futures]

    @skipUnlessDBFeature('has_select_for_update')
    def test_two_connections_reconciling_same_payment_deduct_once(self):
        payment = make_payment([(self.product, 2)])
        self.assertEqual(self.concurrently([payment, payment]), ['paid', 'paid'])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)

    @skipUnlessDBFeature('has_select_for_update')
    def test_competing_orders_cannot_oversell_shared_product(self):
        first = make_payment([(self.product, 2)])
        second = make_payment([(self.product, 2)])
        self.assertCountEqual(self.concurrently([first, second]), ['paid', 'payment_review'])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)

    @skipUnlessDBFeature('has_select_for_update')
    @override_settings(SHOP_CURRENCY='EUR', MOMO_CURRENCY='EUR')
    @patch('orders.views.send_order_placement_notification')
    @patch('orders.views.MomoCollectionClient')
    def test_concurrent_same_checkout_attempt_creates_one_order_and_one_provider_call(self, provider, notification):
        data = {'customer_name': 'Buyer', 'email': 'buyer@example.com', 'phone_number': '26876123456',
            'meta_event_id': str(uuid.uuid4()), 'items': [{'product_id': self.product.pk, 'quantity': 1}]}
        barrier = Barrier(2)

        def submit():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                response = APIClient().post('/api/checkout/momo/', data, format='json')
                return response.status_code, response.data['payment_reference']
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit) for _ in range(2)]
            responses = [future.result(timeout=20) for future in futures]
        self.assertCountEqual([response[0] for response in responses], [200, 201])
        self.assertEqual(responses[0][1], responses[1][1])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        provider.return_value.request_to_pay.assert_called_once()
