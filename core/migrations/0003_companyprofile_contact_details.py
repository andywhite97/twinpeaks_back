from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_companyprofile_social_links")]

    operations = [
        migrations.AddField(model_name="companyprofile", name="address", field=models.TextField(blank=True)),
        migrations.AddField(model_name="companyprofile", name="business_hours", field=models.TextField(blank=True)),
        migrations.AddField(model_name="companyprofile", name="copyright_text", field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name="companyprofile", name="email", field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name="companyprofile", name="phone", field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name="companyprofile", name="whatsapp", field=models.CharField(blank=True, max_length=50)),
    ]
