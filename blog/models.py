import math
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags
from .html import clean_article


class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('display_order', 'name')
        verbose_name_plural = 'Blog categories'

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    excerpt = models.TextField(max_length=400)
    body = models.TextField(help_text='Use the formatting toolbar. Only safe article formatting is retained.')
    cover_image = models.ImageField(upload_to='blog/covers/', blank=True)
    cover_alt = models.CharField(max_length=240, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    author_name = models.CharField(max_length=120, default='TwinPeaks Team', help_text='Public byline; staff account details are never exposed.')
    category = models.ForeignKey(BlogCategory, null=True, blank=True, on_delete=models.SET_NULL)
    solutions = models.ManyToManyField('services.Solution', blank=True, related_name='blog_posts')
    status = models.CharField(max_length=12, choices=[('draft', 'Draft'), ('published', 'Published')], default='draft')
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True, help_text='Required to publish. Future dates stay private until this time.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-published_at', '-pk')
        indexes = [models.Index(fields=['status', 'published_at'])]

    def clean(self):
        self.body = clean_article(self.body)
        errors = {}
        if not strip_tags(self.body).strip():
            errors['body'] = 'Write some article content.'
        if self.status == 'published' and not self.published_at:
            errors['published_at'] = 'Choose a publication date.'
        if self.cover_image and not self.cover_alt.strip():
            errors['cover_alt'] = 'Describe the cover image for readers using assistive technology.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.body = clean_article(self.body)
        super().save(*args, **kwargs)

    @property
    def reading_minutes(self):
        return max(1, math.ceil(len(strip_tags(self.body).split()) / 200))

    @classmethod
    def published(cls):
        return cls.objects.filter(status='published', published_at__lte=timezone.now())

    def __str__(self):
        return self.title
