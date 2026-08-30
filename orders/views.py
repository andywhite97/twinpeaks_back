from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from .models import Order, OrderItem, Payment
from .momo import MomoCollectionClient, MomoConfigurationError, MomoRequestError
from .meta import send_purchase
from .serializers import CheckoutSerializer


def payment_response(order):
    return {
        "order_id": str(order.public_id), "payment_reference": str(order.payment.reference_id),
        "order_status": order.status, "payment_status": order.payment.status,
        "amount": f"{order.subtotal:.2f}", "currency": order.currency, "meta_event_id": str(order.payment.meta_event_id or ""),
    }


def reconcile_payment(payment, provider_data):
    provider_status = provider_data.get("status", "").upper()
    payment.provider_status = provider_status
    payment.provider_transaction_id = provider_data.get("financialTransactionId", "")
    if provider_status == "SUCCESSFUL":
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=payment.order_id)
            payment = Payment.objects.select_for_update().get(pk=payment.pk)
            if payment.status != Payment.Status.SUCCESSFUL:
                for item in order.items.select_related("product").select_for_update():
                    updated = Product.objects.filter(pk=item.product_id, stock_quantity__gte=item.quantity).update(stock_quantity=F("stock_quantity") - item.quantity)
                    if not updated:
                        order.status = Order.Status.PAYMENT_REVIEW
                        order.save(update_fields=["status", "updated_at"])
                        payment.save(update_fields=["provider_status", "provider_transaction_id", "updated_at"])
                        return order
                payment.status = Payment.Status.SUCCESSFUL
                payment.save(update_fields=["status", "provider_status", "provider_transaction_id", "updated_at"])
                order.status = Order.Status.PAID
                order.save(update_fields=["status", "updated_at"])
            return order
    if provider_status in {"FAILED", "REJECTED", "TIMEOUT"}:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "provider_status", "provider_transaction_id", "updated_at"])
        payment.order.status = Order.Status.PAYMENT_FAILED
        payment.order.save(update_fields=["status", "updated_at"])
    else:
        payment.save(update_fields=["provider_status", "provider_transaction_id", "updated_at"])
    return payment.order


class MomoCheckoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if settings.SHOP_CURRENCY != settings.MOMO_CURRENCY:
            return Response({"detail": "Checkout currency is not configured for this MTN MoMo environment."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        data = serializer.validated_data
        with transaction.atomic():
            product_ids = [item["product_id"] for item in data["items"]]
            products = Product.objects.select_for_update().filter(pk__in=product_ids, is_active=True)
            products_by_id = {product.pk: product for product in products}
            if len(products_by_id) != len(product_ids):
                return Response({"detail": "One or more products are no longer available."}, status=status.HTTP_400_BAD_REQUEST)
            total = Decimal("0.00")
            line_items = []
            for item in data["items"]:
                product = products_by_id[item["product_id"]]
                if product.stock_quantity < item["quantity"] or product.price is None:
                    return Response({"detail": f"{product.name} is unavailable in the requested quantity."}, status=status.HTTP_400_BAD_REQUEST)
                unit_price = product.sale_price if product.sale_price is not None else product.price
                line_total = unit_price * item["quantity"]
                total += line_total
                line_items.append((product, item["quantity"], unit_price, line_total))
            order = Order.objects.create(customer_name=data["customer_name"], email=data["email"], phone_number=data["phone_number"], notes=data.get("notes", ""), subtotal=total, currency=settings.SHOP_CURRENCY)
            for product, quantity, unit_price, line_total in line_items:
                OrderItem.objects.create(order=order, product=product, product_name=product.name, product_slug=product.slug, unit_price=unit_price, quantity=quantity, line_total=line_total)
            try:
                reference_id = MomoCollectionClient().request_to_pay(amount=total, currency=settings.MOMO_CURRENCY, phone_number=order.phone_number, external_id=order.public_id)
            except (MomoConfigurationError, MomoRequestError) as exc:
                order.status = Order.Status.PAYMENT_FAILED
                order.save(update_fields=["status", "updated_at"])
                return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            Payment.objects.create(order=order, reference_id=reference_id, amount=total, currency=settings.MOMO_CURRENCY, meta_event_id=data.get("meta_event_id"), event_source_url=data.get("event_source_url", ""))
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
