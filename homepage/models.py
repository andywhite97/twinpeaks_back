from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class HomepageSettings(TimeStampedModel):
    hero_heading = models.CharField(max_length=200, default="Premium technology solutions for modern businesses")
    hero_subheading = models.TextField(default="We build modern digital experiences and reliable systems that help brands grow with confidence.")
    hero_background_image = models.ImageField(upload_to="homepage/", blank=True, null=True)
    hero_primary_cta_text = models.CharField(max_length=80, default="Request a consultation")
    hero_primary_cta_url = models.CharField(max_length=255, default="/contact")
    hero_secondary_cta_text = models.CharField(max_length=80, default="Explore services")
    hero_secondary_cta_url = models.CharField(max_length=255, default="/services")
    trust_badges = models.TextField(blank=True, help_text="One badge per line")

    class Meta:
        verbose_name = "Homepage Settings"
        verbose_name_plural = "Homepage Settings"

    def __str__(self):
        return "Homepage Settings"


class HeroSlide(TimeStampedModel):
    title = models.CharField(max_length=150)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to="homepage/slides/")
    button_text = models.CharField(max_length=80, blank=True)
    button_url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title


class Solution(TimeStampedModel):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=80, blank=True, help_text="Use a simple icon name or class")
    button_text = models.CharField(max_length=80, blank=True)
    button_url = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["display_order", "created_at"]
        verbose_name_plural = "Solutions"

    def __str__(self):
        return self.title


class Statistic(TimeStampedModel):
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=50)
    suffix = models.CharField(max_length=20, blank=True)
    prefix = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return self.label


class Project(TimeStampedModel):
    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to="homepage/projects/")
    completion_date = models.DateField(blank=True, null=True)
    link_url = models.CharField(max_length=255, blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Brand(TimeStampedModel):
    name = models.CharField(max_length=120)
    logo = models.ImageField(upload_to="homepage/brands/")
    website = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return self.name


class Testimonial(TimeStampedModel):
    customer_name = models.CharField(max_length=120)
    business = models.CharField(max_length=150, blank=True)
    photo = models.ImageField(upload_to="homepage/testimonials/", blank=True, null=True)
    rating = models.PositiveIntegerField(default=5)
    review = models.TextField()

    class Meta:
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return self.customer_name
