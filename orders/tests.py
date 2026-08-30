from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import override_settings
from rest_framework.test import APITestCase

from products.models import Product
from .models import Order, Payment


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
