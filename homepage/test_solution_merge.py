from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HomepageSolutionMergeTests(TransactionTestCase):
    def restore_schema(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_transfer_preserves_catalog_content_ids_media_and_visibility(self):
        self.addCleanup(self.restore_schema)
        targets = [("homepage", "0006_rename_solution_homepagesolution"), ("services", "0004_rename_service_solution")]
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        historical = executor.loader.project_state(targets).apps
        Catalog = historical.get_model("services", "Solution")
        Homepage = historical.get_model("homepage", "HomepageSolution")
        existing = Catalog.objects.create(title="Web & App Development", description="Catalog scope", image="solutions/images/web.png")
        blank = Catalog.objects.create(title="Network Infrastructure", description="")
        Homepage.objects.create(title="Web and App Development", description="Old fallback")
        Homepage.objects.create(title="Network Infrastructure", description="Recovered scope")
        Homepage.objects.create(title="Additional solution", description="Unique scope")
        Homepage.objects.create(title="Private solution", description="Hidden scope", is_active=False)
        self.restore_schema()
        Solution = apps.get_model("services", "Solution")
        self.assertEqual(Solution.objects.count(), 4)
        self.assertEqual(Solution.objects.get(pk=existing.pk).description, "Catalog scope")
        self.assertEqual(Solution.objects.get(pk=existing.pk).image.name, "solutions/images/web.png")
        self.assertEqual(Solution.objects.get(pk=blank.pk).description, "Recovered scope")
        self.assertEqual(Solution.objects.get(title="Additional solution").description, "Unique scope")
        self.assertFalse(Solution.objects.get(title="Private solution").is_active)
        self.assertNotIn("homepage_homepagesolution", connection.introspection.table_names())
