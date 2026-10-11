from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("contact", "0004_remove_quotation_converted_order_and_more"),
        ("services", "0004_rename_service_solution"),
    ]
    operations = [migrations.RenameField(model_name="quotationitem", old_name="service", new_name="solution")]
