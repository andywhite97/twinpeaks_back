from django.conf import settings
from django.db import migrations, models


def rename_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    alias = schema_editor.connection.alias
    for action in ("add", "change", "delete", "view"):
        for permission in Permission.objects.using(alias).filter(
            content_type__app_label="services", content_type__model__in=["service", "solution"],
            codename=f"{action}_service",
        ).iterator():
            target = Permission.objects.using(alias).filter(content_type_id=permission.content_type_id, codename=f"{action}_solution").first()
            if target:
                for group in Group.objects.using(alias).filter(permissions=permission).iterator():
                    group.permissions.add(target)
                for user in User.objects.using(alias).filter(user_permissions=permission).iterator():
                    user.user_permissions.add(target)
                permission.delete(using=alias)
            else:
                permission.codename = f"{action}_solution"
                permission.name = f"Can {action} solution"
                permission.save(using=alias, update_fields=["codename", "name"])


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0003_service_image"),
        ("contact", "0004_remove_quotation_converted_order_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.RenameModel(old_name="Service", new_name="Solution"),
        migrations.AlterField(model_name="solution", name="icon", field=models.ImageField(blank=True, null=True, upload_to="solutions/icons/")),
        migrations.AlterField(model_name="solution", name="image", field=models.ImageField(blank=True, null=True, upload_to="solutions/images/", help_text="Optional main solution image (PNG, JPEG or WebP).")),
        migrations.RunPython(rename_permissions, migrations.RunPython.noop),
    ]
