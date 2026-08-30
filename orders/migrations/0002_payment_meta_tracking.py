from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]
    operations = [
        migrations.AddField(model_name="payment", name="event_source_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="payment", name="meta_event_id", field=models.UUIDField(blank=True, null=True, unique=True)),
        migrations.AddField(model_name="payment", name="meta_event_sent", field=models.BooleanField(default=False)),
    ]
