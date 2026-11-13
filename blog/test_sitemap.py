from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import BlogPost


@override_settings(PUBLIC_SITE_URL='https://twinpeaksinvestment.com')
class BlogSitemapTests(TestCase):
    def test_sitemap_lists_only_current_public_articles(self):
        for slug, status, date in [
            ('public-guide', 'published', timezone.now() - timedelta(days=1)),
            ('draft-guide', 'draft', timezone.now()),
            ('future-guide', 'published', timezone.now() + timedelta(days=1)),
        ]:
            BlogPost.objects.create(title=slug, slug=slug, status=status, published_at=date, body='<p>Guide</p>')
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'https://twinpeaksinvestment.com/blog/public-guide')
        self.assertNotContains(response, 'draft-guide')
        self.assertNotContains(response, 'future-guide')
        self.assertNotContains(response, '/newsletter/')
