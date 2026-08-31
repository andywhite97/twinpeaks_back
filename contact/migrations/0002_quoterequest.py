from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("contact", "0001_initial"),
        ("products", "0004_productimage"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuoteRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(blank=True, max_length=150)),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("phone_number", models.CharField(max_length=20)),
                ("message", models.TextField()),
                ("status", models.CharField(choices=[("new", "New"), ("in_progress", "In progress"), ("quoted", "Quoted"), ("closed", "Closed")], default="new", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quote_requests", to="products.product")),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
