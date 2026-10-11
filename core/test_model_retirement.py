from decimal import Decimal
import uuid

from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ModelRetirementMigrationTests(TransactionTestCase):
    old_targets = [
        ("contact", "0003_quotation_workflow"),
        ("orders", "0003_orderitem_product_nullable"),
        ("products", "0004_productimage"),
        ("homepage", "0004_brand_slug_remove_brand_website"),
        ("gallery", "0001_initial"),
        ("leadership", "0003_leader_is_active"),
    ]

    def restore_schema(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_retirement_preserves_existing_quotation_snapshots_and_tokens(self):
        self.addCleanup(self.restore_schema)
        executor = MigrationExecutor(connection)
        executor.migrate(self.old_targets)
        historical = executor.loader.project_state(self.old_targets).apps
        Product = historical.get_model("products", "Product")
        Order = historical.get_model("orders", "Order")
        Quote = historical.get_model("contact", "Quotation")
        Item = historical.get_model("contact", "QuotationItem")
        product = Product.objects.create(name="Legacy camera", slug="legacy-camera", description="Legacy equipment specification", price="25.00")
        order = Order.objects.create(customer_name="Customer", email="customer@example.invalid", phone_number="26876123456", subtotal="50.00", currency="SZL", status="paid")
        token = uuid.uuid4()
        quote = Quote.objects.create(quote_number="TP-Q-2026-0020", public_access_token=token, name="Customer", email="customer@example.invalid", phone_number="26876123456", status="converted_to_order", converted_order=order, internal_notes="Existing note", subtotal="50.00", total="50.00")
        item = Item.objects.create(quotation=quote, product=product, title="", description="", quantity=2, unit_price="25.00", line_total="50.00")
        custom = Item.objects.create(quotation=quote, product=product, title="Agreed specification", description="Preserved custom scope", quantity=1, unit_price="0", line_total="0")

        self.restore_schema()

        Quotation = apps.get_model("contact", "Quotation")
        QuotationItem = apps.get_model("contact", "QuotationItem")
        quote = Quotation.objects.get(pk=quote.pk)
        item = QuotationItem.objects.get(pk=item.pk)
        custom = QuotationItem.objects.get(pk=custom.pk)
        self.assertEqual(quote.public_access_token, token)
        self.assertEqual(quote.status, "converted_to_order")
        self.assertEqual(quote.total, Decimal("50.00"))
        self.assertIn("Existing note", quote.internal_notes)
        self.assertIn(str(order.public_id), quote.internal_notes)
        self.assertEqual(item.title, "Legacy camera")
        self.assertEqual(item.description, "Legacy equipment specification")
        self.assertEqual(item.line_total, Decimal("50.00"))
        self.assertEqual(custom.title, "Agreed specification")
        self.assertEqual(custom.description, "Preserved custom scope")
        retired = {
            "homepage": ["Brand", "HeroSlide", "Statistic", "Testimonial"],
            "products": ["Product", "ProductImage", "ProductCategory"],
            "orders": ["Order", "OrderItem", "Payment"],
            "gallery": ["GalleryItem"], "leadership": ["Leader"],
        }
        tables = connection.introspection.table_names()
        for app, models in retired.items():
            for model in models:
                self.assertNotIn(app + "_" + model.lower(), tables)
                with self.assertRaises(LookupError):
                    apps.get_model(app, model)
