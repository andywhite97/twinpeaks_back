import uuid
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("contact", "0002_quoterequest"), ("orders", "0002_payment_meta_tracking"), ("services", "0002_service_icon")]
    operations = [
        migrations.RenameModel("QuoteRequest", "Quotation"),
        migrations.CreateModel(name="QuotationSequence", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("year", models.PositiveIntegerField(unique=True)), ("next_number", models.PositiveIntegerField(default=1))]),
        migrations.RemoveField(model_name="quotation", name="product"),
        migrations.RemoveField(model_name="quotation", name="product_name"),
        migrations.AddField(model_name="quotation", name="quote_number", field=models.CharField(default=uuid.uuid4, editable=False, max_length=36, unique=True), preserve_default=False),
        migrations.AddField(model_name="quotation", name="public_access_token", field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
        migrations.AddField(model_name="quotation", name="company_name", field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name="quotation", name="address", field=models.TextField(blank=True)),
        migrations.AddField(model_name="quotation", name="internal_notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="quotation", name="terms", field=models.TextField(blank=True)),
        migrations.AddField(model_name="quotation", name="subtotal", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        migrations.AddField(model_name="quotation", name="discount_amount", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        migrations.AddField(model_name="quotation", name="tax_amount", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        migrations.AddField(model_name="quotation", name="total", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        migrations.AddField(model_name="quotation", name="currency", field=models.CharField(default="SZL", max_length=3)),
        migrations.AddField(model_name="quotation", name="valid_until", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="sent_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="viewed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="accepted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="declined_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="quotation", name="decline_reason", field=models.CharField(blank=True, max_length=500)),
        migrations.AddField(model_name="quotation", name="converted_order", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_quotation", to="orders.order")),
        migrations.AlterField(model_name="quotation", name="status", field=models.CharField(choices=[("draft","Draft"),("requested","Requested"),("under_review","Under review"),("sent","Sent"),("viewed","Viewed"),("accepted","Accepted"),("declined","Declined"),("expired","Expired"),("converted_to_order","Converted to order"),("cancelled","Cancelled")], default="requested", max_length=24)),
        migrations.CreateModel(name="QuotationItem", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("title", models.CharField(max_length=150)), ("description", models.TextField(blank=True)), ("quantity", models.PositiveIntegerField(default=1)), ("unit_price", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)), ("discount_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)), ("tax_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)), ("line_total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)), ("sort_order", models.PositiveIntegerField(default=0)), ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="products.product")), ("service", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="services.service")), ("quotation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="contact.quotation"))], options={"ordering": ("sort_order", "id")}),
    ]
