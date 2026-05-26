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

    def __str__(self):
        return self.name
