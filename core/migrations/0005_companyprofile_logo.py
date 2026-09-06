from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_clear_legacy_invoice_migration_history")]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to="company/"),
        ),
    ]
