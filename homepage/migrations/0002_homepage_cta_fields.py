from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("homepage", "0001_initial")]

    operations = [
        migrations.AddField(model_name="homepagesettings", name="cta_background_image", field=models.ImageField(blank=True, null=True, upload_to="homepage/cta/")),
        migrations.AddField(model_name="homepagesettings", name="cta_heading", field=models.CharField(default="Excited to start your next project?", max_length=200)),
        migrations.AddField(model_name="homepagesettings", name="cta_primary_button_text", field=models.CharField(default="Request a quote", max_length=80)),
        migrations.AddField(model_name="homepagesettings", name="cta_primary_button_url", field=models.CharField(default="/contact", max_length=255)),
        migrations.AddField(model_name="homepagesettings", name="cta_secondary_button_text", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="homepagesettings", name="cta_secondary_button_url", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="homepagesettings", name="cta_subheading", field=models.TextField(blank=True)),
    ]
