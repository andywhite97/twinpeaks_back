from rest_framework.test import APITestCase

from homepage.models import Brand
from .models import Product


class ProductBrandFilterTests(APITestCase):
    def test_products_can_be_filtered_by_brand_slug(self):
        hikvision = Brand.objects.create(name="Hikvision", slug="hikvision", logo="brands/hikvision.png")
        dahua = Brand.objects.create(name="Dahua", slug="dahua", logo="brands/dahua.png")
        Product.objects.create(name="Hikvision camera", slug="hikvision-camera", description="", brand=hikvision)
        Product.objects.create(name="Dahua camera", slug="dahua-camera", description="", brand=dahua)

        response = self.client.get("/api/products/?brand=hikvision")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([product["slug"] for product in response.data["results"]], ["hikvision-camera"])
