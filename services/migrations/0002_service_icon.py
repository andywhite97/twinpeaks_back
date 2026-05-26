# Generated for service icons

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="icon",
            field=models.ImageField(blank=True, null=True, upload_to="services/icons/"),
        ),
    ]
