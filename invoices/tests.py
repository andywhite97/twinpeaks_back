from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Invoice


class InvoiceGenerateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.admin)

    def test_generates_invoice_workbook_from_payload(self):
        response = self.client.post(
            "/api/invoices/generate/",
            {
                "customer": {
                    "name": "Acme Projects",
                    "location": "Mbabane",
                    "email": "accounts@example.com",
                    "phone": "+268 1234 5678",
                },
                "invoice_number": "INV-001",
                "customer_id": "CUST-001",
                "date": "2026-06-03",
                "due_date": "2026-06-30",
                "salesperson": "TwinPeaks Admin",
                "job": "Consulting",
                "payment_terms": "Due on receipt",
                "items": [
                    {
                        "quantity": "2",
                        "description": "Site assessment",
                        "unit_price": "100.00",
                    },
                    {
                        "quantity": "1",
                        "description": "Report preparation",
                        "unit_price": "50.00",
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        content = b"".join(response.streaming_content)
        with ZipFile(BytesIO(content)) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")

        self.assertIn("Acme Projects", sheet)
        self.assertIn("INV-001", sheet)
        self.assertIn("Site assessment", sheet)
        self.assertIn("<v>250.00</v>", sheet)
        self.assertIn("<v>37.50</v>", sheet)
        self.assertIn("<v>287.50</v>", sheet)

        invoice = Invoice.objects.get(invoice_number="INV-001")
        self.assertEqual(invoice.customer_name, "Acme Projects")
        self.assertEqual(invoice.subtotal, 250)
        self.assertEqual(invoice.tax, 37.5)
        self.assertEqual(invoice.total, 287.5)
        self.assertEqual(invoice.generated_by, self.admin)
