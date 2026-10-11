from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class SolutionRenameMigrationTests(TransactionTestCase):
    old_targets = [
        ("services", "0003_service_image"),
        ("contact", "0004_remove_quotation_converted_order_and_more"),
        ("homepage", "0005_delete_brand_delete_heroslide_delete_statistic_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("users", "0001_initial"),
    ]

    def restore_schema(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_model_renames_keep_ids_media_paths_and_quotation_links(self):
        self.addCleanup(self.restore_schema)
        executor = MigrationExecutor(connection)
        executor.migrate(self.old_targets)
        historical = executor.loader.project_state(self.old_targets).apps
        Service = historical.get_model("services", "Service")
        HomepageSolution = historical.get_model("homepage", "Solution")
        Quote = historical.get_model("contact", "Quotation")
        Item = historical.get_model("contact", "QuotationItem")
        service = Service.objects.create(title="Network Infrastructure", description="Existing description", icon="services/icons/network.png", image="services/images/network.png")
        homepage = HomepageSolution.objects.create(title="Network Infrastructure", description="Homepage fallback")
        quote = Quote.objects.create(quote_number="TP-Q-2026-0021", name="Customer", email="customer@example.invalid", phone_number="26876123456")
        item = Item.objects.create(quotation=quote, service=service, title=service.title)
        ContentType = historical.get_model("contenttypes", "ContentType")
        Permission = historical.get_model("auth", "Permission")
        Group = historical.get_model("auth", "Group")
        group = Group.objects.create(name="Catalog editors")
        for app, model in [("services", "service"), ("homepage", "solution")]:
            content_type, _ = ContentType.objects.get_or_create(app_label=app, model=model)
            permission, _ = Permission.objects.get_or_create(content_type=content_type, codename="view_" + model, defaults={"name": "Legacy view permission"})
            group.permissions.add(permission)
        rename_targets = [
            ("services", "0004_rename_service_solution"),
            ("contact", "0005_rename_service_solution"),
            ("homepage", "0006_rename_solution_homepagesolution"),
        ]
        executor = MigrationExecutor(connection)
        executor.migrate(rename_targets)
        renamed_apps = executor.loader.project_state(rename_targets).apps
        solution = apps.get_model("services", "Solution").objects.get(pk=service.pk)
        item = apps.get_model("contact", "QuotationItem").objects.get(pk=item.pk)
        self.assertEqual(solution.title, "Network Infrastructure")
        self.assertEqual(solution.image.name, "services/images/network.png")
        self.assertEqual(solution.icon.name, "services/icons/network.png")
        self.assertEqual(item.solution_id, solution.pk)
        self.assertEqual(renamed_apps.get_model("homepage", "HomepageSolution").objects.get(pk=homepage.pk).description, "Homepage fallback")
        group = apps.get_model("auth", "Group").objects.get(pk=group.pk)
        self.assertTrue(group.permissions.filter(content_type__app_label="services", codename="view_solution").exists())
        self.assertTrue(group.permissions.filter(content_type__app_label="homepage", codename="view_homepagesolution").exists())
