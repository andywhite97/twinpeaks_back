from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leadership", "0002_leader_facebook_leader_linkedin")]

    operations = [
        migrations.AddField(
            model_name="leader",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
