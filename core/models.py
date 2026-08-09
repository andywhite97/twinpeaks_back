from django.db import models


class CompanyProfile(models.Model):
    name = models.CharField(max_length=150)
    tagline = models.CharField(max_length=200)
    overview = models.TextField()
    vision = models.TextField()
    mission = models.TextField()
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    business_hours = models.TextField(blank=True)
    copyright_text = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name
