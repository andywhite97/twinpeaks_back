from django.contrib.sitemaps import Sitemap
from django.conf import settings
from homepage.models import Project
from products.models import Product
from urllib.parse import urlsplit


class PublicSitemap(Sitemap):
    """Generate entries for the frontend domain even when hosted by the API."""

    protocol = "https"

    def get_urls(self, page=1, site=None, protocol=None):
        public_url = urlsplit(settings.PUBLIC_SITE_URL)
        site = type("PublicSite", (), {"domain": public_url.netloc, "name": "Twinpeaks"})()
        return super().get_urls(page=page, site=site, protocol=self.protocol)


class StaticViewSitemap(PublicSitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["/", "/products", "/services", "/projects", "/about", "/contact"]

    def location(self, item):
        return item


class ProductSitemap(PublicSitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return f"/products/{obj.slug}"


class ProjectSitemap(PublicSitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Project.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/projects/{obj.slug}"
