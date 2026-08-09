from django.core.cache import cache
from rest_framework.test import APITestCase

from products.models import Product, ProductCategory
from .models import HomepageSettings


class HomepageApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        HomepageSettings.objects.create(hero_heading="A backend-managed homepage")
        category = ProductCategory.objects.create(name="CCTV", slug="cctv", is_featured=True)
        Product.objects.create(
            name="Featured camera",
            slug="featured-camera",
            description="A featured product.",
            category=category,
            stock_quantity=5,
            is_featured=True,
        )

    def test_homepage_payload_contains_featured_content(self):
        response = self.client.get("/api/homepage/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["hero"]["hero_heading"], "A backend-managed homepage")
        self.assertEqual(response.data["featured_categories"][0]["slug"], "cctv")
        self.assertEqual(response.data["featured_products"][0]["slug"], "featured-camera")
