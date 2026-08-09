from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("homepage", "0002_homepage_cta_fields")]

    operations = [
        migrations.AddField(model_name="project", name="long_description", field=models.TextField(blank=True)),
        migrations.CreateModel(
            name="ProjectImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="homepage/projects/")),
                ("caption", models.CharField(blank=True, max_length=150)),
                ("display_order", models.PositiveIntegerField(default=0)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="homepage.project")),
            ],
            options={"ordering": ["display_order", "id"]},
        ),
    ]
