from decimal import Decimal
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from .models import Order, OrderItem, Payment
from .momo import MomoAmbiguousError, MomoCollectionClient, MomoConfigurationError, MomoRequestError
from .reconciliation import reconcile_payment
from .meta import send_purchase
from .serializers import CheckoutSerializer
from .tasks import send_order_placement_notification


def payment_response(order):
    return {
        "order_id": str(order.public_id), "payment_reference": str(order.payment.reference_id),
        "order_status": order.status, "payment_status": order.payment.status,
        "amount": f"{order.subtotal:.2f}", "currency": order.currency, "meta_event_id": str(order.payment.meta_event_id or ""),
    }


def existing_checkout_response(payment, data):
    """Same attempt may be replayed, but never applied to a different basket/customer."""
    order = payment.order
    requested = sorted((item['product_id'], item['quantity']) for item in data['items'])
    actual = sorted((item.product_id, item.quantity) for item in order.items.all())
    fields = ('customer_name', 'email', 'phone_number', 'notes')
    if requested != actual or any(getattr(order, field) != data.get(field, '') for field in fields):
        return Response({'detail': 'This payment attempt belongs to a different checkout.'}, status=status.HTTP_409_CONFLICT)
    return Response(payment_response(order), status=status.HTTP_200_OK)


class MomoCheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if settings.SHOP_CURRENCY != settings.MOMO_CURRENCY:
            return Response({"detail": "Checkout currency is not configured for this MTN MoMo environment."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        data = serializer.validated_data
        event_id = data.get('meta_event_id')
        if event_id:
            existing = Payment.objects.select_related('order').filter(meta_event_id=event_id).first()
            if existing:
                return existing_checkout_response(existing, data)
        try:
            with transaction.atomic():
                product_ids = [item['product_id'] for item in data['items']]
                products_by_id = {product.pk: product for product in Product.objects.select_for_update()
                                  .filter(pk__in=product_ids, is_active=True).order_by('pk')}
                if len(products_by_id) != len(product_ids):
                    return Response({'detail': 'One or more products are no longer available.'}, status=status.HTTP_400_BAD_REQUEST)
                total = Decimal('0.00')
                line_items = []
                for item in data['items']:
                    product = products_by_id[item['product_id']]
                    if product.stock_quantity < item['quantity'] or product.price is None:
                        return Response({'detail': f'{product.name} is unavailable in the requested quantity.'}, status=status.HTTP_400_BAD_REQUEST)
                    unit_price = product.sale_price if product.sale_price is not None else product.price
                    line_total = unit_price * item['quantity']
                    total += line_total
                    line_items.append((product, item['quantity'], unit_price, line_total))
                order = Order.objects.create(customer_name=data['customer_name'], email=data['email'],
                    phone_number=data['phone_number'], notes=data.get('notes', ''), subtotal=total, currency=settings.SHOP_CURRENCY)
                for product, quantity, unit_price, line_total in line_items:
                    OrderItem.objects.create(order=order, product=product, product_name=product.name,
                        product_slug=product.slug, unit_price=unit_price, quantity=quantity, line_total=line_total)
                # Persist the exact provider reference before any external payment call.
                payment = Payment.objects.create(order=order, reference_id=uuid.uuid4(), amount=total,
                    currency=settings.MOMO_CURRENCY, meta_event_id=event_id, provider_status='REQUESTING',
                    event_source_url=data.get('event_source_url', ''))
        except IntegrityError:
            if not event_id:
                raise
            existing = Payment.objects.select_related('order').filter(meta_event_id=event_id).first()
            if not existing:
                raise
            return existing_checkout_response(existing, data)

        # No row locks remain during network calls. A retry returns this record;
        # it never submits another request-to-pay, even after an ambiguous timeout.
        try:
            MomoCollectionClient().request_to_pay(amount=total, currency=payment.currency,
                phone_number=order.phone_number, external_id=order.public_id, reference_id=payment.reference_id)
        except MomoAmbiguousError:
            with transaction.atomic():
                locked_order = Order.objects.select_for_update().get(pk=order.pk)
                locked_payment = Payment.objects.select_for_update().get(pk=payment.pk)
                if locked_payment.status == Payment.Status.PENDING and locked_payment.provider_status == 'REQUESTING':
                    locked_order.status = Order.Status.PAYMENT_REVIEW
                    locked_order.save(update_fields=['status', 'updated_at'])
                    locked_payment.provider_status = 'REQUEST_UNKNOWN'
                    locked_payment.save(update_fields=['provider_status', 'updated_at'])
        except (MomoConfigurationError, MomoRequestError):
            # Authentication failure or definitive rejection occurred before an
            # accepted charge. Never overwrite a concurrent provider success.
            with transaction.atomic():
                locked_order = Order.objects.select_for_update().get(pk=order.pk)
                locked_payment = Payment.objects.select_for_update().get(pk=payment.pk)
                if locked_payment.status == Payment.Status.PENDING and locked_payment.provider_status == 'REQUESTING':
                    locked_payment.status = Payment.Status.FAILED
                    locked_payment.provider_status = 'REQUEST_REJECTED'
                    locked_payment.save(update_fields=['status', 'provider_status', 'updated_at'])
                    locked_order.status = Order.Status.PAYMENT_FAILED
                    locked_order.save(update_fields=['status', 'updated_at'])
        send_order_placement_notification(order.pk)
        order.refresh_from_db()
        return Response(payment_response(order), status=status.HTTP_201_CREATED)


class MomoPaymentStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, reference_id):
        try:
            payment = Payment.objects.select_related("order").get(reference_id=reference_id)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
        if payment.status == Payment.Status.PENDING:
            try:
                order = reconcile_payment(payment, MomoCollectionClient().get_status(payment.reference_id))
            except (MomoConfigurationError, MomoRequestError) as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        else:
            order = payment.order
        order.refresh_from_db()
        payment.refresh_from_db()
        if order.status == Order.Status.PAID and not payment.meta_event_sent and send_purchase(payment, request):
            payment.meta_event_sent = True
            payment.save(update_fields=["meta_event_sent", "updated_at"])
        return Response(payment_response(order))
