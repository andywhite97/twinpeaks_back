from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("products", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ProductCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="product-categories/")),
                ("description", models.TextField(blank=True)),
                ("is_featured", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("display_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["display_order", "name"], "verbose_name_plural": "Product categories"},
        ),
        migrations.AddField(model_name="product", name="category", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="products.productcategory")),
        migrations.AddField(model_name="product", name="installation_available", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="product", name="is_featured", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="product", name="rating", field=models.DecimalField(decimal_places=2, default=0, max_digits=3)),
        migrations.AddField(model_name="product", name="sale_price", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="product", name="stock_quantity", field=models.PositiveIntegerField(default=0)),
    ]
