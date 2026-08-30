from decimal import Decimal
import uuid
from unittest.mock import Mock, patch
import requests

from django.test import override_settings
from django.test.client import RequestFactory
from rest_framework.test import APITestCase

from products.models import Product
from .models import Order, Payment
from .meta import _hash, purchase_payload, send_purchase


@override_settings(
    SHOP_CURRENCY="EUR", MOMO_CURRENCY="EUR", MOMO_COLLECTION_SUBSCRIPTION_KEY="subscription",
    MOMO_COLLECTION_API_USER="api-user", MOMO_COLLECTION_API_KEY="api-key",
)
class MomoCheckoutTests(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Camera", slug="camera", description="", price=Decimal("10.00"), stock_quantity=3)
        self.payload = {"customer_name": "Test Buyer", "email": "buyer@example.com", "phone_number": "26876123456", "items": [{"product_id": self.product.id, "quantity": 2}]}

    @patch("orders.momo.requests.post")
    def test_starts_payment_with_server_calculated_total(self, post):
        token = Mock(ok=True); token.json.return_value = {"access_token": "token"}
        request_to_pay = Mock(status_code=202)
        post.side_effect = [token, request_to_pay]

        response = self.client.post("/api/checkout/momo/", self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_status"], "pending")
        self.assertEqual(response.data["amount"], "20.00")
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(post.call_args_list[1].kwargs["json"]["amount"], "20.00")

    @patch("orders.momo.requests.get")
    @patch("orders.momo.requests.post")
    def test_successful_status_marks_order_paid_and_reduces_stock(self, post, get):
        token = Mock(ok=True); token.json.return_value = {"access_token": "token"}
        post.side_effect = [token, Mock(status_code=202)]
        created = self.client.post("/api/checkout/momo/", self.payload, format="json")
        token_for_status = Mock(ok=True); token_for_status.json.return_value = {"access_token": "token"}
        status_response = Mock(ok=True); status_response.json.return_value = {"status": "SUCCESSFUL", "financialTransactionId": "provider-1"}
        post.side_effect = [token_for_status]
        get.return_value = status_response

        response = self.client.get(f"/api/checkout/momo/{created.data['payment_reference']}/")

        self.assertEqual(response.data["order_status"], "paid")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)


@override_settings(META_PIXEL_ID="pixel-id", META_CONVERSIONS_API_ACCESS_TOKEN="token")
class MetaConversionsTests(APITestCase):
    def test_purchase_payload_uses_slug_event_id_and_hashed_customer_data(self):
        product = Product.objects.create(name="Camera", slug="catalog-camera", description="", price="25.00", stock_quantity=1)
        order = Order.objects.create(customer_name="Buyer", email="BUYER@EXAMPLE.COM", phone_number="26876123456", subtotal="25.00", currency="SZL", status=Order.Status.PAID)
        from .models import OrderItem
        OrderItem.objects.create(order=order, product=product, product_name=product.name, product_slug=product.slug, unit_price="25.00", quantity=1, line_total="25.00")
        payment = Payment.objects.create(order=order, reference_id=uuid.uuid4(), meta_event_id=uuid.uuid4(), amount="25.00", currency="SZL", event_source_url="https://twinpeaksinvestment.com/cart")

        payload = purchase_payload(payment, RequestFactory().get("/api/checkout/momo/", HTTP_USER_AGENT="test-agent"))

        event = payload["data"][0]
        self.assertEqual(event["event_id"], str(payment.meta_event_id))
        self.assertEqual(event["custom_data"]["content_ids"], ["catalog-camera"])
        self.assertEqual(event["custom_data"]["currency"], "SZL")
        self.assertEqual(event["user_data"]["em"], [_hash("buyer@example.com")])
        self.assertNotIn("BUYER@EXAMPLE.COM", str(payload))

    @patch("orders.meta.requests.post", side_effect=requests.ConnectionError("network unavailable"))
    def test_meta_failure_does_not_raise(self, post):
        product = Product.objects.create(name="Camera", slug="camera", description="", price="1.00", stock_quantity=1)
        order = Order.objects.create(customer_name="Buyer", email="buyer@example.com", phone_number="26876123456", subtotal="1.00", currency="SZL", status=Order.Status.PAID)
        payment = Payment.objects.create(order=order, reference_id=uuid.uuid4(), meta_event_id=uuid.uuid4(), amount="1.00", currency="SZL", event_source_url="https://twinpeaksinvestment.com/cart")

        self.assertFalse(send_purchase(payment, RequestFactory().get("/")))
