from django.conf import settings
from django.db import migrations


def rename_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    alias = schema_editor.connection.alias
    for action in ("add", "change", "delete", "view"):
        for permission in Permission.objects.using(alias).filter(content_type__app_label="homepage", content_type__model__in=["solution", "homepagesolution"], codename=f"{action}_solution").iterator():
            target = Permission.objects.using(alias).filter(content_type_id=permission.content_type_id, codename=f"{action}_homepagesolution").first()
            if target:
                for group in Group.objects.using(alias).filter(permissions=permission).iterator():
                    group.permissions.add(target)
                for user in User.objects.using(alias).filter(user_permissions=permission).iterator():
                    user.user_permissions.add(target)
                permission.delete(using=alias)
            else:
                permission.codename = f"{action}_homepagesolution"
                permission.name = f"Can {action} homepage solution"
                permission.save(using=alias, update_fields=["codename", "name"])


class Migration(migrations.Migration):
    dependencies = [
        ("homepage", "0005_delete_brand_delete_heroslide_delete_statistic_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.RenameModel(old_name="Solution", new_name="HomepageSolution"),
        migrations.AlterModelOptions(name="homepagesolution", options={"ordering": ["display_order", "created_at"], "verbose_name": "Homepage solution", "verbose_name_plural": "Homepage solutions"}),
        migrations.RunPython(rename_permissions, migrations.RunPython.noop),
    ]
