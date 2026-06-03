from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import Product

from .models import Customer, Invoice, InvoiceItem


class InvoiceGenerateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="password123",
        )
        self.client.force_authenticate(self.admin)
        self.assessment = Product.objects.create(
            name="Site assessment",
            slug="site-assessment",
            description="Site assessment service",
            price="100.00",
        )
        self.report = Product.objects.create(
            name="Report preparation",
            slug="report-preparation",
            description="Report preparation service",
            price="50.00",
        )

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
                "date": "2026-06-03",
                "due_date": "2026-06-30",
                "salesperson": "TwinPeaks Admin",
                "job": "Consulting",
                "payment_terms": "Due on receipt",
                "items": [
                    {
                        "product": self.assessment.id,
                        "quantity": "2",
                    },
                    {
                        "product": self.report.id,
                        "quantity": "1",
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
        customer = Customer.objects.get(email="accounts@example.com")
        self.assertIn(customer.customer_id, sheet)
        self.assertIn("<v>250.00</v>", sheet)
        self.assertIn("<v>37.50</v>", sheet)
        self.assertIn("<v>287.50</v>", sheet)

        invoice = Invoice.objects.get(invoice_number="INV-001")
        self.assertEqual(invoice.customer, customer)
        self.assertEqual(invoice.customer.name, "Acme Projects")
        self.assertEqual(invoice.status, Invoice.Status.QUOTE)
        self.assertEqual(invoice.subtotal, 250)
        self.assertEqual(invoice.tax, 37.5)
        self.assertEqual(invoice.total, 287.5)
        self.assertEqual(invoice.generated_by, self.admin)
        self.assertEqual(invoice.line_items.count(), 2)
        line_item = invoice.line_items.get(product=self.assessment)
        self.assertEqual(line_item.product_name, "Site assessment")
        self.assertEqual(line_item.unit_price, 100)
        self.assertEqual(line_item.line_total, 200)

    def test_updates_existing_customer_when_generating_invoice(self):
        customer = Customer.objects.create(
            email="accounts@example.com",
            name="Old Name",
            location="Old Location",
            phone="000",
        )

        response = self.client.post(
            "/api/invoices/generate/",
            {
                "customer": {
                    "name": "Acme Projects",
                    "location": "Mbabane",
                    "email": "accounts@example.com",
                    "phone": "+268 1234 5678",
                },
                "invoice_number": "INV-002",
                "items": [
                    {
                        "product": self.assessment.id,
                        "quantity": "1",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Acme Projects")
        self.assertEqual(customer.location, "Mbabane")
        self.assertEqual(customer.phone, "+268 1234 5678")
        self.assertEqual(Invoice.objects.get(invoice_number="INV-002").customer, customer)

    def test_can_mark_quote_as_invoice(self):
        customer = Customer.objects.create(
            email="accounts@example.com",
            name="Acme Projects",
        )
        invoice = Invoice.objects.create(
            invoice_number="INV-003",
            customer=customer,
            invoice_date="2026-06-03",
            subtotal="100.00",
            tax="15.00",
            total="115.00",
            items=[],
            generated_by=self.admin,
        )

        response = self.client.patch(
            f"/api/invoices/{invoice.id}/status/",
            {"status": Invoice.Status.INVOICE},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.INVOICE)
        self.assertEqual(response.data["status"], Invoice.Status.INVOICE)

    def test_invoice_item_price_is_locked_when_product_price_changes(self):
        response = self.client.post(
            "/api/invoices/generate/",
            {
                "customer": {
                    "name": "Acme Projects",
                    "email": "accounts@example.com",
                },
                "invoice_number": "INV-004",
                "items": [
                    {
                        "product": self.assessment.id,
                        "quantity": "1",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assessment.price = "150.00"
        self.assessment.save()

        line_item = InvoiceItem.objects.get(invoice__invoice_number="INV-004")
        invoice = Invoice.objects.get(invoice_number="INV-004")
        self.assertEqual(line_item.unit_price, 100)
        self.assertEqual(line_item.line_total, 100)
        self.assertEqual(invoice.subtotal, 100)
