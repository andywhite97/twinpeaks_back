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

    def test_related_products_prioritise_the_same_brand(self):
        brand = Brand.objects.create(name="Hikvision", slug="hikvision", logo="brands/hikvision.png")
        product = Product.objects.create(name="Main camera", slug="main-camera", description="", brand=brand)
        related = Product.objects.create(name="Related camera", slug="related-camera", description="", brand=brand)

        response = self.client.get(f"/api/products/{product.slug}/related/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["slug"] for item in response.data], [related.slug])
