from django.core.cache import cache
from rest_framework.test import APITestCase

from .models import HomepageSettings, Project
from services.models import Solution


class HomepageApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        HomepageSettings.objects.create(hero_heading="A backend-managed homepage")
        Solution.objects.create(title="Network Infrastructure", description="Published solution", image="solutions/images/network.png")
        Solution.objects.create(title="Hidden solution", description="Unpublished", is_active=False)
        Project.objects.create(title="Published installation", image="homepage/projects/network.png", is_featured=True)

    def test_homepage_payload_contains_featured_content(self):
        response = self.client.get("/api/homepage/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["hero"]["hero_heading"], "A backend-managed homepage")
        self.assertEqual(response.data["solutions"][0]["title"], "Network Infrastructure")
        self.assertEqual(response.data["projects"][0]["title"], "Published installation")
        self.assertEqual(set(response.data), {"hero", "settings", "solutions", "projects"})

    def test_homepage_and_catalog_publish_the_same_solution_records(self):
        homepage = self.client.get("/api/homepage/")
        catalog = self.client.get("/api/solutions/")
        self.assertEqual(homepage.data["solutions"], catalog.data)
        self.assertEqual(len(catalog.data), 1)
        self.assertEqual(catalog.data[0]["image"], "http://testserver/media/solutions/images/network.png")
        self.assertEqual(self.client.get("/api/homepage-solutions/").status_code, 404)
