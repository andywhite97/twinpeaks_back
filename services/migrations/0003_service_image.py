from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("services", "0002_service_icon")]

    operations = [
        migrations.AddField(
            model_name="service",
            name="image",
            field=models.ImageField(
                blank=True, null=True, upload_to="services/images/",
                help_text="Optional main service image (PNG, JPEG or WebP).",
            ),
        ),
    ]
