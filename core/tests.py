from django.test import TestCase, override_settings

from products.models import Product


@override_settings(PUBLIC_SITE_URL="https://twinpeaksinvestment.com")
class SitemapTests(TestCase):
    def test_sitemap_uses_frontend_product_urls(self):
        Product.objects.create(name="Camera", slug="camera", description="", is_active=True)

        response = self.client.get("/sitemap.xml", HTTP_HOST="backend.twinpeaksinvestment.com")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://twinpeaksinvestment.com/products/camera")
