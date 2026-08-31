from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("orders", "0002_payment_meta_tracking")]
    operations = [migrations.AlterField(model_name="orderitem", name="product", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="products.product"))]
