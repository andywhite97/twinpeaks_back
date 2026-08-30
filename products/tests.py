import csv
from io import StringIO

from django.test import override_settings
from rest_framework.test import APITestCase

from homepage.models import Brand
from .models import Product, ProductCategory, ProductImage


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


@override_settings(
    ALLOWED_HOSTS=["api.example.test", "testserver"],
    META_CATALOG_STOREFRONT_URL="https://twinpeaksinvestment.com",
)
class MetaCatalogFeedTests(APITestCase):
    def test_feed_returns_meta_compatible_rows_for_active_products(self):
        category = ProductCategory.objects.create(name="Security Cameras", slug="security-cameras")
        brand = Brand.objects.create(name="Hikvision", slug="hikvision", logo="brands/hikvision.jpg")
        product = Product.objects.create(
            name="Camera, \"Pro\"",
            slug="camera-pro",
            description='Clear, reliable "security" camera.',
            price="850",
            sale_price="799.5",
            image="products/camera.jpg",
            category=category,
            brand=brand,
            stock_quantity=4,
        )
        ProductImage.objects.create(product=product, image="products/gallery/camera.jpg")
        Product.objects.create(
            name="Inactive camera",
            slug="inactive-camera",
            description="Not public",
            price="1",
            image="products/inactive.jpg",
            is_active=False,
        )

        response = self.client.get("/api/meta/catalog-feed.csv", HTTP_HOST="api.example.test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        rows = list(csv.DictReader(StringIO(response.content.decode())))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], product.slug)
        self.assertEqual(row["title"], product.name)
        self.assertEqual(row["description"], product.description)
        self.assertEqual(row["availability"], "in stock")
        self.assertEqual(row["price"], "850.00 SZL")
        self.assertEqual(row["sale_price"], "799.50 SZL")
        self.assertEqual(row["link"], "https://twinpeaksinvestment.com/products/camera-pro")
        self.assertTrue(row["image_link"].startswith("https://"))
        self.assertTrue(row["additional_image_link"].startswith("https://"))
        self.assertEqual(row["brand"], "Hikvision")
        self.assertEqual(row["product_type"], "Security Cameras")

    def test_feed_marks_zero_stock_products_out_of_stock(self):
        Product.objects.create(
            name="Out of stock camera",
            slug="out-of-stock-camera",
            description="Out of stock",
            price="10",
            image="products/out-of-stock.jpg",
            stock_quantity=0,
        )

        response = self.client.get("/api/meta/catalog-feed.csv", HTTP_HOST="api.example.test")

        row = next(csv.DictReader(StringIO(response.content.decode())))
        self.assertEqual(row["availability"], "out of stock")
