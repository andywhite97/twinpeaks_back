# Generated for CompanyProfile social links

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyprofile",
            name="facebook",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="companyprofile",
            name="twitter",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="companyprofile",
            name="instagram",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="companyprofile",
            name="linkedin",
            field=models.URLField(blank=True, null=True),
        ),
    ]
