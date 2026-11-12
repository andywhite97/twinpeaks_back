from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from .html import clean_article
from .models import BlogCategory, BlogPost


class BlogTests(TestCase):
    def setUp(self):
        self.category = BlogCategory.objects.create(name='Security', slug='security')
        self.post = BlogPost.objects.create(title='Published guide', slug='published-guide', excerpt='Useful advice', body='<p>Hello <strong>world</strong></p>', status='published', published_at=timezone.now(), category=self.category)
        BlogPost.objects.create(title='Draft', slug='draft', body='<p>Private</p>')
        BlogPost.objects.create(title='Future', slug='future', body='<p>Private</p>', status='published', published_at=timezone.now()+timedelta(days=1))

    def test_only_public_articles_are_exposed(self):
        result = self.client.get('/api/blog/posts/').json()
        self.assertEqual(result['count'], 1)
        self.assertNotIn('body', result['results'][0])
        self.assertNotIn('author', result['results'][0])
        self.assertEqual(self.client.get('/api/blog/posts/draft/').status_code, 404)
        self.assertEqual(self.client.get('/api/blog/posts/future/').status_code, 404)
        self.assertEqual(self.client.get('/api/blog/posts/published-guide/').json()['body'], self.post.body)

    def test_category_and_pagination(self):
        self.assertEqual(self.client.get('/api/blog/posts/?category=unknown').json()['count'], 0)
        self.assertEqual(self.client.get('/api/blog/posts/?category=security').json()['count'], 1)
        self.assertEqual(self.client.get('/api/blog/posts/?page=999').status_code, 404)

    def test_html_cannot_execute_code(self):
        result = clean_article('<script>alert(1)</script><img src=x onerror=alert(1)><p onclick="x()">Text</p><a href="javascript:alert(1)">Link</a><a href="https://example.com">Good</a>')
        self.assertNotIn('<script', result)
        self.assertNotIn('<img', result)
        self.assertNotIn('onclick', result)
        self.assertNotIn('javascript:', result)
        self.assertIn('href="https://example.com"', result)
        self.assertEqual(clean_article('<a href="https://[bad">test</a>'), '<a>test</a>')

    def test_preview_requires_staff_permission(self):
        url = f'/admin/blog/blogpost/{self.post.pk}/preview/'
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_superuser(email='editor@example.com', password='test-password')
        self.client.force_login(user)
        result = self.client.get(url)
        self.assertEqual(result.status_code, 200)
        self.assertIn('no-store', result['Cache-Control'])

    def test_public_api_rejects_writes(self):
        self.assertEqual(self.client.post('/api/blog/posts/', {}).status_code, 405)
