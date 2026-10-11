from django.test import TestCase, override_settings

from homepage.models import Project


@override_settings(PUBLIC_SITE_URL="https://twinpeaksinvestment.com")
class SitemapTests(TestCase):
    def test_sitemap_uses_current_v2_routes_and_published_project_urls(self):
        Project.objects.create(title="Network installation", slug="network-installation", image="homepage/projects/network.png", is_active=True)

        response = self.client.get("/sitemap.xml", HTTP_HOST="backend.twinpeaksinvestment.com")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://twinpeaksinvestment.com/projects/network-installation")
        self.assertContains(response, "https://twinpeaksinvestment.com/solutions")
        self.assertNotContains(response, "/products")
        self.assertNotContains(response, "/services")


class RetiredEndpointTests(TestCase):
    def test_retired_public_endpoints_are_unavailable(self):
        for path in [
            "/api/products/", "/api/products/old-product/", "/api/categories/", "/api/brands/",
            "/api/meta/catalog-feed.csv", "/api/checkout/momo/", "/api/leaders/",
            "/api/gallery/", "/api/gallery/old-item/", "/api/statistics/", "/api/testimonials/",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
