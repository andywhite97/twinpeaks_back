from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from products.models import Product

from .models import Customer, Invoice, InvoiceItem


class InvoiceGenerateViewTests(TestCase):
    def setUp(self):
        self.media_root = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root.name)
        self.settings_override.enable()
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

    def tearDown(self):
        self.settings_override.disable()
        self.media_root.cleanup()

    def test_generates_invoice_pdf_from_payload_and_emails_customer(self):
        response = self.client.post(
            "/api/invoices/generate/",
            {
                "customer": {
                    "name": "Acme Projects",
                    "location": "Mbabane",
                    "email": "accounts@example.com",
                    "phone": "+268 1234 5678",
                },
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
            "application/pdf",
        )

        content = b"".join(response.streaming_content)
        self.assertTrue(content.startswith(b"%PDF-1.4"))
        self.assertIn(b"QT-20260603-0001", content)
        self.assertIn(b"Acme Projects", content)
        self.assertIn(b"Site assessment", content)

        customer = Customer.objects.get(email="accounts@example.com")

        invoice = Invoice.objects.get(invoice_number="QT-20260603-0001")
        self.assertEqual(invoice.customer, customer)
        self.assertEqual(invoice.customer.name, "Acme Projects")
        self.assertEqual(invoice.status, Invoice.Status.QUOTE)
        self.assertEqual(invoice.subtotal, 250)
        self.assertEqual(invoice.tax, 37.5)
        self.assertEqual(invoice.total, 287.5)
        self.assertEqual(invoice.generated_by, self.admin)
        self.assertEqual(invoice.items.count(), 2)
        line_item = invoice.items.get(product=self.assessment)
        self.assertEqual(line_item.product_name, "Site assessment")
        self.assertEqual(line_item.unit_price, 100)
        self.assertEqual(line_item.line_total, 200)
        self.assertEqual(invoice.invoice_pdf, "invoices/pdfs/QT-20260603-0001.pdf")
        self.assertEqual(
            invoice.invoice_workbook,
            "invoices/workbooks/QT-20260603-0001.xlsx",
        )
        self.assertTrue((Path(self.media_root.name) / invoice.invoice_pdf).exists())
        self.assertTrue((Path(self.media_root.name) / invoice.invoice_workbook).exists())
        self.assertEqual(
            response["X-Invoice-Pdf-Path"],
            str(Path(self.media_root.name) / invoice.invoice_pdf),
        )
        self.assertTrue(response["X-Invoice-Pdf-Url"].endswith(invoice.invoice_pdf))
        self.assertEqual(
            response["X-Invoice-Workbook-Path"],
            str(Path(self.media_root.name) / invoice.invoice_workbook),
        )
        self.assertIn(
            response["X-Invoice-Template-Source"],
            {"invoice_design.xlsx", "fallback-pdf"},
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["accounts@example.com"])
        self.assertEqual(mail.outbox[0].attachments[0][0], "QT-20260603-0001.pdf")
        self.assertEqual(mail.outbox[0].attachments[0][2], "application/pdf")

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
        self.assertEqual(Invoice.objects.get(invoice_number__startswith="QT-").customer, customer)

    def test_can_mark_quote_as_invoice(self):
        customer = Customer.objects.create(
            email="accounts@example.com",
            name="Acme Projects",
        )
        invoice = Invoice.objects.create(
            customer=customer,
            invoice_date="2026-06-03",
            subtotal="100.00",
            tax="15.00",
            total="115.00",
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
        self.assertEqual(invoice.invoice_number, "INV-20260603-0001")
        self.assertEqual(response.data["status"], Invoice.Status.INVOICE)
        self.assertEqual(response.data["invoice_number"], "INV-20260603-0001")

    def test_invoice_item_price_is_locked_when_product_price_changes(self):
        response = self.client.post(
            "/api/invoices/generate/",
            {
                "customer": {
                    "name": "Acme Projects",
                    "email": "accounts@example.com",
                },
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

        invoice = Invoice.objects.get(invoice_number__startswith="QT-")
        line_item = invoice.items.get()
        self.assertEqual(line_item.unit_price, 100)
        self.assertEqual(line_item.line_total, 100)
        self.assertEqual(invoice.subtotal, 100)

    def test_can_mark_invoice_as_paid_with_receipt_number(self):
        customer = Customer.objects.create(
            email="accounts@example.com",
            name="Acme Projects",
        )
        invoice = Invoice.objects.create(
            customer=customer,
            invoice_date="2026-06-03",
            subtotal="100.00",
            tax="15.00",
            total="115.00",
            status=Invoice.Status.INVOICE,
            generated_by=self.admin,
        )

        response = self.client.patch(
            f"/api/invoices/{invoice.id}/status/",
            {"status": Invoice.Status.PAID},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.invoice_number, "RCPT-20260603-0001")
        self.assertEqual(response.data["invoice_number"], "RCPT-20260603-0001")

    def test_invoice_totals_auto_populate_from_items(self):
        customer = Customer.objects.create(
            email="accounts@example.com",
            name="Acme Projects",
        )
        invoice = Invoice.objects.create(
            customer=customer,
            invoice_date="2026-06-03",
            tax_rate="0.1500",
            generated_by=self.admin,
        )
        line_item = InvoiceItem.objects.create(
            product=self.assessment,
            quantity="2",
        )

        invoice.items.add(line_item)
        invoice.refresh_from_db()

        self.assertEqual(invoice.subtotal, 200)
        self.assertEqual(invoice.tax, 30)
        self.assertEqual(invoice.total, 230)

        line_item.quantity = "3"
        line_item.save()
        invoice.refresh_from_db()

        self.assertEqual(invoice.subtotal, 300)
        self.assertEqual(invoice.tax, 45)
        self.assertEqual(invoice.total, 345)
