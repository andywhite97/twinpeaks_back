from django.db import migrations


def merge_solutions(apps, schema_editor):
    HomepageSolution = apps.get_model("homepage", "HomepageSolution")
    Solution = apps.get_model("services", "Solution")
    alias = schema_editor.connection.alias

    def key(title):
        return " ".join(title.lower().replace("&", " and ").split())

    records = {}
    for solution in Solution.objects.using(alias).order_by("pk"):
        records.setdefault(key(solution.title), []).append(solution)
    for source in HomepageSolution.objects.using(alias).order_by("display_order", "created_at"):
        matches = records.get(key(source.title), [])
        if not matches:
            target = Solution.objects.using(alias).create(
                title=source.title, description=source.description, is_active=source.is_active,
            )
            records.setdefault(key(source.title), []).append(target)
        elif len(matches) == 1 and not matches[0].description.strip():
            target = matches[0]
            target.description = source.description
            target.save(using=alias, update_fields=["description"])


class Migration(migrations.Migration):
    dependencies = [
        ("homepage", "0006_rename_solution_homepagesolution"),
        ("services", "0004_rename_service_solution"),
    ]
    operations = [
        migrations.RunPython(merge_solutions, migrations.RunPython.noop),
        migrations.DeleteModel(name="HomepageSolution"),
    ]
