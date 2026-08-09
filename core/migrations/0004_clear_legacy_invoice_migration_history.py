from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0003_companyprofile_contact_details")]

    operations = [
        migrations.RunSQL(
            "DELETE FROM django_migrations WHERE app = 'invoices';",
            migrations.RunSQL.noop,
        ),
    ]
