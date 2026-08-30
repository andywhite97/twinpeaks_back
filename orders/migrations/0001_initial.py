import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("products", "0004_productimage")]
    operations = [
        migrations.CreateModel(name="Order", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ("customer_name", models.CharField(max_length=150)), ("email", models.EmailField(max_length=254)),
            ("phone_number", models.CharField(max_length=20)), ("notes", models.TextField(blank=True)),
            ("subtotal", models.DecimalField(decimal_places=2, max_digits=12)), ("currency", models.CharField(max_length=3)),
            ("status", models.CharField(choices=[("pending_payment", "Pending payment"), ("paid", "Paid"), ("payment_failed", "Payment failed"), ("payment_review", "Payment review"), ("cancelled", "Cancelled")], default="pending_payment", max_length=24)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ("-created_at",)}),
        migrations.CreateModel(name="OrderItem", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("product_name", models.CharField(max_length=150)), ("product_slug", models.SlugField()),
            ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)), ("quantity", models.PositiveIntegerField()), ("line_total", models.DecimalField(decimal_places=2, max_digits=12)),
            ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="orders.order")),
            ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="products.product")),
        ]),
        migrations.CreateModel(name="Payment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("provider", models.CharField(default="mtn_momo", max_length=40)), ("reference_id", models.UUIDField(unique=True)),
            ("status", models.CharField(choices=[("pending", "Pending"), ("successful", "Successful"), ("failed", "Failed")], default="pending", max_length=16)),
            ("provider_status", models.CharField(blank=True, max_length=40)), ("provider_transaction_id", models.CharField(blank=True, max_length=100)),
            ("amount", models.DecimalField(decimal_places=2, max_digits=12)), ("currency", models.CharField(max_length=3)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("order", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="payment", to="orders.order")),
        ]),
    ]
